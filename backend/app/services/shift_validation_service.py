# backend/app/services/shift_validation_service.py
"""シフトアサインのビジネスルール検証サービス層.

``shift_rules_service`` が提供するルール定義に基づいて、
シフトアサインの妥当性を検証する純粋なバリデーターを提供する。
"""

import uuid
from datetime import date, timedelta
from typing import cast

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.models import (
    CustomRule,
    EmploymentType,
    EmploymentTypeRule,
    LongHolidayPeriod,
    LongHolidayTypeEnum,
    PlanStatusEnum,
    Position,
    ShiftAssignment,
    ShiftPlan,
    ShiftRequirement,
    ShiftRequirementAssignment,
    ShiftSlot,
    SlotTypeEnum,
    TenantSkillRank,
    Worker,
    WorkerMonthlySlotStats,
)
from app.models.rule_schemas import (
    AnnualPartialLimitsConfig,
    AnnualShiftLimitsConfig,
    EmploymentTypeRuleConfig,
    ShiftRulesConfig,
    ValidationViolationItem,
)
from app.services.age_utils import calculate_age_at
from app.services.long_holiday_period_service import (
    get_period_for_date,
    is_holiday_type_excluded_by_position,
)


def _load_non_default_employment_type_ids(
    session: Session,
    tenant_id: str,
) -> set[uuid.UUID]:
    """テナント内の非デフォルト雇用形態IDセットを取得する.

    ``is_default=False`` の雇用形態は「特別雇用」扱いとみなされ、
    シフト枠の制限チェックに使用する。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        非デフォルト雇用形態IDのセット。
    """
    non_default_types = session.exec(
        select(EmploymentType).where(
            EmploymentType.tenant_id == tenant_id,
            EmploymentType.is_default.is_(False),  # type: ignore[union-attr]
        )
    ).all()
    return {cast(uuid.UUID, et.id) for et in non_default_types if et.id is not None}


def _load_employment_type_rules(
    session: Session,
    tenant_id: str,
) -> dict[uuid.UUID, EmploymentTypeRuleConfig]:
    """テナント内の雇用形態別ルールをまとめて取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        雇用形態ID -> EmploymentTypeRuleConfig のマッピング。
    """
    rule_rows = session.exec(
        select(EmploymentTypeRule).where(
            EmploymentTypeRule.tenant_id == tenant_id,
        )
    ).all()
    result: dict[uuid.UUID, EmploymentTypeRuleConfig] = {}
    for row in rule_rows:
        overrides_raw = row.annual_limit_overrides
        annual_limit_overrides = (
            AnnualPartialLimitsConfig(**overrides_raw)
            if isinstance(overrides_raw, dict)
            else None
        )
        config = EmploymentTypeRuleConfig(
            require_default_pair=bool(row.require_default_pair),
            allowed_slot_types=row.allowed_slot_types
            if isinstance(row.allowed_slot_types, list)
            else None,
            annual_limit_overrides=annual_limit_overrides,
        )
        et_id = cast(uuid.UUID, row.employment_type_id)
        result[et_id] = config
    return result


def _load_custom_rules_for_workers(
    session: Session,
    tenant_id: str,
    workers: list[Worker],
) -> dict[uuid.UUID, AnnualPartialLimitsConfig | None]:
    """Workerのカスタムルールをまとめて取得する.

    ``custom_rule_id`` が設定されているWorkerのルール設定を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        workers: 対象ワーカーリスト。

    Returns:
        ワーカーID -> (allowed_slot_types, annual_limit_overrides) のマッピング。
    """
    custom_rule_ids = {
        cast(uuid.UUID, w.custom_rule_id)
        for w in workers
        if w.custom_rule_id is not None
    }
    if not custom_rule_ids:
        return {}

    rule_rows = session.exec(
        select(CustomRule).where(
            CustomRule.id.in_(custom_rule_ids),  # type: ignore[attr-defined]
            CustomRule.tenant_id == tenant_id,
        )
    ).all()
    rule_map: dict[uuid.UUID, CustomRule] = {
        cast(uuid.UUID, r.id): r for r in rule_rows
    }

    result: dict[uuid.UUID, AnnualPartialLimitsConfig | None] = {}
    for worker in workers:
        if worker.custom_rule_id is None:
            continue
        cr_id = cast(uuid.UUID, worker.custom_rule_id)
        rule = rule_map.get(cr_id)
        if rule is None:
            continue
        overrides_raw = rule.annual_limit_overrides
        annual_limit_overrides = (
            AnnualPartialLimitsConfig(**overrides_raw)
            if isinstance(overrides_raw, dict)
            else None
        )
        result[cast(uuid.UUID, worker.id)] = annual_limit_overrides
    return result


def _load_worker_custom_rule_objects(
    session: Session,
    tenant_id: str,
    workers: list[Worker],
) -> dict[uuid.UUID, CustomRule | None]:
    """Workerに紐付くCustomRuleオブジェクトをまとめて取得する.

    ``custom_rule_id`` が設定されているWorkerのCustomRuleオブジェクトを返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        workers: 対象ワーカーリスト。

    Returns:
        ワーカーID -> CustomRule（またはNone）のマッピング。
    """
    custom_rule_ids = {
        cast(uuid.UUID, w.custom_rule_id)
        for w in workers
        if w.custom_rule_id is not None
    }
    if not custom_rule_ids:
        return {}

    rule_rows = session.exec(
        select(CustomRule).where(
            CustomRule.id.in_(custom_rule_ids),  # type: ignore[attr-defined]
            CustomRule.tenant_id == tenant_id,
        )
    ).all()
    rule_map: dict[uuid.UUID, CustomRule] = {
        cast(uuid.UUID, r.id): r for r in rule_rows
    }

    result: dict[uuid.UUID, CustomRule | None] = {}
    for worker in workers:
        if worker.custom_rule_id is None:
            continue
        cr_id = cast(uuid.UUID, worker.custom_rule_id)
        rule = rule_map.get(cr_id)
        result[cast(uuid.UUID, worker.id)] = rule
    return result


def _check_daily_duplicate(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
) -> list[ValidationViolationItem]:
    """ルール1: 1人1日1枠チェック（同日に複数枠へのアサイン検出）."""
    violations: list[ValidationViolationItem] = []
    for worker in workers:
        dup = session.exec(
            select(ShiftRequirementAssignment)
            .join(
                ShiftRequirement,
                ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirement.shift_date == requirement.shift_date,
                ShiftRequirementAssignment.requirement_id != requirement.id,  # type: ignore[arg-type]
            )
        ).first()
        if dup:
            violations.append(
                ValidationViolationItem(
                    code="DAILY_DUPLICATE",
                    severity="error",
                    message=f"{worker.name} は同日に複数の枠にアサインされています",
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def _check_same_department(
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """ルール2: 同一所属課ペア禁止チェック."""
    if rules.allow_same_department:
        return []
    seen_dept: set[uuid.UUID] = set()
    dup_dept_worker_ids: list[str] = []
    for w in workers:
        if w.department_id in seen_dept:
            dup_dept_worker_ids = [
                str(w2.id) for w2 in workers if w2.department_id == w.department_id
            ]
            break
        seen_dept.add(cast(uuid.UUID, w.department_id))
    if not dup_dept_worker_ids:
        return []
    return [
        ValidationViolationItem(
            code="SAME_DEPARTMENT",
            severity="error",
            message="同じ所属課のメンバーが同一枠にアサインされています",
            worker_ids=dup_dept_worker_ids,
        )
    ]


def _check_skill_rank(
    session: Session,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """ルール3: リーダー適性チェック（全員アサイン済みの場合のみ）.

    アサインされたWorkerのスキルランクに ``is_leader_eligible=True`` のものが含まれるか検証する。
    """
    if len(workers) < requirement.required_headcount:
        return []
    if not rules.require_skill_ranks:
        return []
    skill_rank_ids = [w.skill_rank_id for w in workers if w.skill_rank_id is not None]
    if not skill_rank_ids:
        return [
            ValidationViolationItem(
                code="SKILL_RANK_A",
                severity="error",
                message="リーダー適性（is_leader_eligible）を持つメンバーが含まれていません",
                worker_ids=[str(w.id) for w in workers],
            )
        ]
    eligible_rank = session.exec(
        select(TenantSkillRank).where(
            TenantSkillRank.id.in_(skill_rank_ids),  # type: ignore[attr-defined]
            TenantSkillRank.is_leader_eligible.is_(True),  # type: ignore[attr-defined]
        )
    ).first()
    if eligible_rank:
        return []
    return [
        ValidationViolationItem(
            code="SKILL_RANK_A",
            severity="error",
            message="リーダー適性（is_leader_eligible）を持つメンバーが含まれていません",
            worker_ids=[str(w.id) for w in workers],
        )
    ]


def _check_work_interval(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """ルール4: 中N日以上の勤務間隔チェック（月跨ぎ対応）.

    同月内の ShiftRequirementAssignment に加え、前月の確定済み（published）
    ShiftPlan の ShiftSlot/ShiftAssignment も検索対象に含める。
    これにより月を跨いだアサイン（例: 3月31日 → 4月1日）でも
    min_interval_days を遵守しているか検証できる。
    """
    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    date_from = shift_date - timedelta(days=rules.min_interval_days - 1)
    date_to = shift_date + timedelta(days=rules.min_interval_days - 1)

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        found_violation = False

        # ShiftRequirementAssignment ベースのチェック（日付範囲でフィルタリング済み）
        nearby_reqs = session.exec(
            select(ShiftRequirement)
            .join(
                ShiftRequirementAssignment,
                ShiftRequirement.id == ShiftRequirementAssignment.requirement_id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirementAssignment.requirement_id != requirement.id,  # type: ignore[arg-type]
                ShiftRequirement.tenant_id == tenant_id,
                ShiftRequirement.shift_date >= date_from,
                ShiftRequirement.shift_date <= date_to,
            )
        ).all()

        for other_req in nearby_reqs:
            other_date: date = other_req.shift_date  # type: ignore[assignment]
            diff = abs((shift_date - other_date).days)
            if diff < rules.min_interval_days:
                violations.append(
                    ValidationViolationItem(
                        code="WORK_INTERVAL",
                        severity="error",
                        message=(
                            f"{worker.name} の勤務間隔が"
                            f"中{rules.min_interval_days - 1}日を満たしていません"
                            f"（{diff - 1}日間隔）"
                        ),
                        worker_ids=[str(worker.id)],
                    )
                )
                found_violation = True
                break

        if found_violation:
            continue

        # ShiftSlot/ShiftAssignment ベースのチェック（確定済み ShiftPlan のみ）
        # 前月の published シフトデータと月跨ぎ間隔を検証する
        published_slot_dates = session.exec(
            select(ShiftSlot.date)
            .join(ShiftAssignment, ShiftAssignment.slot_id == ShiftSlot.id)  # type: ignore[arg-type]
            .join(ShiftPlan, ShiftPlan.id == ShiftSlot.plan_id)  # type: ignore[arg-type]
            .where(
                ShiftAssignment.worker_id == worker.id,
                ShiftSlot.tenant_id == tenant_id,
                ShiftPlan.status == PlanStatusEnum.published,
                ShiftSlot.date >= date_from,
                ShiftSlot.date <= date_to,
            )
        ).all()

        for slot_date_raw in published_slot_dates:
            # ShiftSlot.date は DateTime 型のため date に変換
            slot_date_val: date = (
                slot_date_raw.date()
                if hasattr(slot_date_raw, "date")
                else slot_date_raw  # type: ignore[assignment]
            )
            diff = abs((shift_date - slot_date_val).days)
            if 0 < diff < rules.min_interval_days:
                violations.append(
                    ValidationViolationItem(
                        code="WORK_INTERVAL",
                        severity="error",
                        message=(
                            f"{worker.name} の勤務間隔が"
                            f"中{rules.min_interval_days - 1}日を満たしていません"
                            f"（{diff - 1}日間隔）"
                        ),
                        worker_ids=[str(worker.id)],
                    )
                )
                break

    return violations


def _check_assign_prohibited(
    workers: list[Worker],
    worker_custom_rules: dict[uuid.UUID, CustomRule | None] | None = None,
) -> list[ValidationViolationItem]:
    """カスタムルール: アサイン不可チェック.

    ``is_assign_prohibited=True`` のカスタムルールが設定されているWorkerは
    全スロットへのアサインを禁止する。

    Args:
        workers: バリデーション対象のWorkerリスト。
        worker_custom_rules: ワーカーID -> CustomRuleオブジェクトのマッピング。

    Returns:
        バリデーション違反アイテムのリスト。
    """
    violations: list[ValidationViolationItem] = []
    custom_rules = worker_custom_rules or {}

    for worker in workers:
        worker_id = cast(uuid.UUID, worker.id)
        custom_rule = custom_rules.get(worker_id)
        if custom_rule is not None and custom_rule.is_assign_prohibited:
            violations.append(
                ValidationViolationItem(
                    code="ASSIGN_PROHIBITED",
                    severity="error",
                    message=(
                        f"{worker.name} はアサイン不可ルールにより、"
                        "いずれの枠にもアサインできません"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )

    return violations


def _check_special_employment(
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
    non_default_employment_type_ids: set[uuid.UUID],
    employment_type_rules: dict[uuid.UUID, EmploymentTypeRuleConfig] | None = None,
    worker_custom_rules: dict[uuid.UUID, CustomRule | None] | None = None,
) -> list[ValidationViolationItem]:
    """ルール5: 特別雇用者の枠制限チェック.

    非デフォルト雇用形態（``is_default=False``）に紐付くワーカーは、
    ``special_employment_shifts`` で許可された枠以外にはアサインできない。
    優先順位: カスタムルール > 雇用形態別ルール > グローバルルール。
    カスタムルールがアサインされているワーカーは、雇用形態にかかわらず制限チェックを受ける。
    """
    slot_type_str = str(requirement.slot_type)
    violations: list[ValidationViolationItem] = []
    custom_rules = worker_custom_rules or {}

    for worker in workers:
        worker_id = cast(uuid.UUID, worker.id)
        custom_rule = custom_rules.get(worker_id)

        # is_assign_prohibited=True の Worker は _check_assign_prohibited の責務に委ねる
        if custom_rule is not None and custom_rule.is_assign_prohibited:
            continue

        # カスタムルールが設定されており allowed_slot_types が指定されている場合は最優先
        if (
            custom_rule is not None
            and isinstance(custom_rule.allowed_slot_types, list)
            and custom_rule.allowed_slot_types
        ):
            allowed_slots = set(custom_rule.allowed_slot_types)
            if slot_type_str not in allowed_slots:
                allowed_slots_str = "、".join(custom_rule.allowed_slot_types)
                violations.append(
                    ValidationViolationItem(
                        code="SPECIAL_EMPLOYMENT",
                        severity="error",
                        message=(
                            f"{worker.name} のカスタムルールにより、"
                            f"許可された枠（{allowed_slots_str}）以外にはアサインできません"
                        ),
                        worker_ids=[str(worker.id)],
                    )
                )
            continue

        # カスタムルールがない場合は雇用形態ベースのチェック
        if worker.employment_type_id is None:
            continue
        et_id = cast(uuid.UUID, worker.employment_type_id)
        if et_id not in non_default_employment_type_ids:
            continue

        # 雇用形態別ルールの allowed_slot_types を優先的に使用
        et_rule = (employment_type_rules or {}).get(et_id)
        if et_rule is not None and et_rule.allowed_slot_types is not None:
            allowed_slots = set(et_rule.allowed_slot_types)
            allowed_slots_str = "、".join(et_rule.allowed_slot_types)
        else:
            # グローバル設定にフォールバック
            allowed_slots = set(rules.special_employment_shifts)
            allowed_slots_str = "、".join(rules.special_employment_shifts)

        if slot_type_str not in allowed_slots:
            violations.append(
                ValidationViolationItem(
                    code="SPECIAL_EMPLOYMENT",
                    severity="error",
                    message=(
                        f"{worker.name} は特別雇用者のため、"
                        f"許可された枠（{allowed_slots_str}）以外にはアサインできません"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def _check_employment_pair_restriction(
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
    non_default_employment_type_ids: set[uuid.UUID],
    employment_type_rules: dict[uuid.UUID, EmploymentTypeRuleConfig] | None = None,
) -> list[ValidationViolationItem]:
    """ペア制限チェック（require_default_pair）.

    ``require_default_pair=True`` の雇用形態を持つWorkerをアサインする際、
    ペア相手にデフォルト雇用形態（``is_default=True``）のWorkerが含まれていなければならない。

    ``workers_per_slot=1`` の場合はこのチェックをスキップする。
    """
    if rules.workers_per_slot <= 1:
        return []
    if len(workers) < 2:
        return []

    et_rules = employment_type_rules or {}
    violations: list[ValidationViolationItem] = []

    # デフォルト雇用形態のWorkerが存在するか確認
    has_default_et_worker = any(
        worker.employment_type_id is not None
        and worker.employment_type_id not in non_default_employment_type_ids
        for worker in workers
    )

    for worker in workers:
        if worker.employment_type_id is None:
            continue
        et_id = cast(uuid.UUID, worker.employment_type_id)
        et_rule = et_rules.get(et_id)
        if et_rule is None or not et_rule.require_default_pair:
            continue

        if not has_default_et_worker:
            violations.append(
                ValidationViolationItem(
                    code="EMPLOYMENT_PAIR_RESTRICTION",
                    severity="error",
                    message=(
                        f"{worker.name} の雇用形態はペア相手にデフォルト雇用形態のスタッフが必須です"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )

    return violations


def _check_age_restriction(
    workers: list[Worker],
    shift_date: date,
) -> list[ValidationViolationItem]:
    """ルール6: 年齢制限チェック（ペアの年齢合計が120歳以下であること）.

    シフト対象日の属する月の初日を基準日として年齢を計算する。
    ペア（2名）の年齢合計が120歳を超える場合はエラーとなる。
    """
    reference_date = shift_date.replace(day=1)

    workers_with_birth_date = [w for w in workers if w.birth_date is not None]
    if len(workers_with_birth_date) < 2:
        return []

    age_sum = sum(
        calculate_age_at(cast(date, w.birth_date), reference_date)
        for w in workers_with_birth_date
    )
    if age_sum <= 120:
        return []

    return [
        ValidationViolationItem(
            code="AGE_SUM_EXCEEDED",
            severity="error",
            message=(
                f"ペアの年齢合計が120歳を超えています（合計: {age_sum}歳）。"
                "年齢合計が120歳以下のペアを組んでください"
            ),
            worker_ids=[str(w.id) for w in workers_with_birth_date],
        )
    ]


def _check_position_exclusion(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
) -> list[ValidationViolationItem]:
    """ルール7: 役職除外チェック.

    - is_excluded_from_all_shifts=True の役職はシフト種別に関わらず全アサイン禁止。
    - 長期休暇期間中は、休暇種別に応じた除外フラグも評価する。
    """
    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    period = get_period_for_date(session, tenant_id, shift_date)

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        if worker.position_id is None:
            continue
        position = session.exec(
            select(Position).where(
                Position.id == worker.position_id,  # type: ignore[arg-type]
                Position.tenant_id == tenant_id,
            )
        ).first()
        if position is None:
            continue
        # is_excluded_from_all_shifts は長期休暇期間外でも適用する
        if position.is_excluded_from_all_shifts:
            violations.append(
                ValidationViolationItem(
                    code="POSITION_EXCLUDED",
                    severity="error",
                    message=(
                        f"{worker.name} の役職（{position.name}）は"
                        f"全シフトへのアサインが除外されています"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
            continue
        # 長期休暇期間中は休暇種別ごとの除外フラグを評価する
        if period is not None and is_holiday_type_excluded_by_position(
            cast(LongHolidayTypeEnum, period.holiday_type), position
        ):  # type: ignore[arg-type]
            violations.append(
                ValidationViolationItem(
                    code="POSITION_EXCLUDED",
                    severity="error",
                    message=(
                        f"{worker.name} の役職（{position.name}）は"
                        f"長期休暇期間（{period.holiday_type}）中のアサインが除外されています"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def _check_tenure_restriction(
    workers: list[Worker],
    shift_date: date,
    rules: ShiftRulesConfig | None = None,
) -> list[ValidationViolationItem]:
    """ルール8: 着任・異動後の期間制限チェック.

    - 採用（transfer_type=hired）: joined_at から hired_tenure_months ヶ月経過していない場合はアサイン不可。
    - 事業本部間転入（transfer_type=transfer_in かつ is_cross_division_transfer=True）:
      異動日（transferred_at または joined_at）から cross_division_transfer_tenure_months ヶ月経過していない場合はアサイン不可。
    閾値が 0 の場合は制限なし。
    """
    from app.models.models import TransferTypeEnum

    hired_months = rules.hired_tenure_months if rules is not None else 6
    transfer_months = (
        rules.cross_division_transfer_tenure_months if rules is not None else 3
    )

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        worker_transfer_type = worker.transfer_type

        # 採用（hired）: joined_at から hired_tenure_months ヶ月チェック
        if worker_transfer_type == TransferTypeEnum.hired:
            if hired_months > 0 and worker.joined_at is not None:
                months_since_joined = _months_between(worker.joined_at, shift_date)  # type: ignore[arg-type]
                if months_since_joined < hired_months:
                    violations.append(
                        ValidationViolationItem(
                            code="NEW_HIRE_TENURE",
                            severity="error",
                            message=(
                                f"{worker.name} は採用後{hired_months}ヶ月経過していません"
                                f"（着任日: {worker.joined_at}、あと"
                                f" {hired_months - months_since_joined} ヶ月必要）"
                            ),
                            worker_ids=[str(worker.id)],
                        )
                    )
            continue

        # 事業本部間転入: transferred_at または joined_at から transfer_months ヶ月チェック
        if (
            worker_transfer_type == TransferTypeEnum.transfer_in
            and worker.is_cross_division_transfer
        ):
            if transfer_months > 0:
                transfer_date: date | None = (
                    worker.transferred_at  # type: ignore[assignment]
                    if worker.transferred_at is not None
                    else worker.joined_at  # type: ignore[assignment]
                )
                if transfer_date is not None:
                    months_since_transfer = _months_between(transfer_date, shift_date)
                    if months_since_transfer < transfer_months:
                        violations.append(
                            ValidationViolationItem(
                                code="TRANSFER_TENURE",
                                severity="error",
                                message=(
                                    f"{worker.name} は事業本部間異動後{transfer_months}ヶ月経過していません"
                                    f"（異動日: {transfer_date}、あと"
                                    f" {transfer_months - months_since_transfer} ヶ月必要）"
                                ),
                                worker_ids=[str(worker.id)],
                            )
                        )
    return violations


def _months_between(start_date: date, end_date: date) -> int:
    """2つの日付間の完全な月数を計算する（切り捨て）."""
    total_months = (end_date.year - start_date.year) * 12 + (
        end_date.month - start_date.month
    )
    if end_date.day < start_date.day:
        total_months -= 1
    return max(0, total_months)


def _check_sun_hol_day_monthly_limit(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
) -> list[ValidationViolationItem]:
    """ルール9: 日曜・祝日昼間シフトの月1回制限チェック.

    sun_hol_day 枠に対して、同月内に既にアサイン済みの場合はエラーとなる。
    """
    if str(requirement.slot_type) != SlotTypeEnum.sun_hol_day:
        return []

    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    month_start = shift_date.replace(day=1)
    import calendar

    last_day = calendar.monthrange(shift_date.year, shift_date.month)[1]
    month_end = shift_date.replace(day=last_day)

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        existing = session.exec(
            select(ShiftRequirementAssignment)
            .join(
                ShiftRequirement,
                ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirement.slot_type == SlotTypeEnum.sun_hol_day,
                ShiftRequirement.shift_date >= month_start,
                ShiftRequirement.shift_date <= month_end,
                ShiftRequirementAssignment.requirement_id != requirement.id,  # type: ignore[arg-type]
            )
        ).first()
        if existing:
            violations.append(
                ValidationViolationItem(
                    code="SUN_HOL_DAY_MONTHLY_LIMIT",
                    severity="error",
                    message=(
                        f"{worker.name} は当月の日曜・祝日昼間シフトに既にアサインされています"
                        "（月1回まで）"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def _check_long_holiday_prev_year_exclusion(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
) -> list[ValidationViolationItem]:
    """ルール10: 前年GW・年末年始参加者の当年同シフト除外チェック.

    対象日が長期連休期間（GWまたは年末年始）に該当する場合、
    前年の同期間にシフトに入ったスタッフは当年の同シフトから外す。
    """
    shift_date: date = requirement.shift_date  # type: ignore[assignment]

    # 対象日が長期連休期間かどうかを確認
    current_period = get_period_for_date(session, tenant_id, shift_date)
    if current_period is None:
        return []
    if current_period.holiday_type not in (
        LongHolidayTypeEnum.gw,
        LongHolidayTypeEnum.year_end,
    ):
        return []

    # 前年の同種の長期連休期間を取得
    prev_year = shift_date.year - 1
    prev_period = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.tenant_id == tenant_id,
            LongHolidayPeriod.holiday_type == current_period.holiday_type,
            LongHolidayPeriod.year == prev_year,
        )
    ).first()
    if prev_period is None:
        return []

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        prev_year_assignment = session.exec(
            select(ShiftRequirementAssignment)
            .join(
                ShiftRequirement,
                ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirement.shift_date >= prev_period.start_date,
                ShiftRequirement.shift_date <= prev_period.end_date,
            )
        ).first()
        if prev_year_assignment:
            holiday_name = (
                "GW"
                if current_period.holiday_type == LongHolidayTypeEnum.gw
                else "年末年始"
            )
            violations.append(
                ValidationViolationItem(
                    code="LONG_HOLIDAY_PREV_YEAR_EXCLUSION",
                    severity="error",
                    message=(
                        f"{worker.name} は前年の{holiday_name}シフトに参加済みのため、"
                        f"当年の同シフトへのアサインはできません"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


_SLOT_ANNUAL_LABEL: dict[str, str] = {
    "weekday_night": "平日夜間",
    "sat_day": "土曜昼間",
    "sat_night": "土曜夜間",
    "sun_hol_day": "日祝昼間",
    "sun_hol_night": "日祝夜間",
    "sat_pre_hol_night": "土曜・祝前日夜間",
}


def _count_annual_slots(slot_types: list[str]) -> tuple[int, dict[str, int]]:
    """スロット種別リストから年間集計（合計, 種別別カウント）を算出する.

    long_hol_day / long_hol_night はそれぞれ sun_hol_day / sun_hol_night に合算する。
    """
    counts: dict[str, int] = {k: 0 for k in _SLOT_ANNUAL_LABEL}
    total = 0
    for st in slot_types:
        total += 1
        if st == "long_hol_day":
            counts["sun_hol_day"] += 1
        elif st == "long_hol_night":
            counts["sun_hol_night"] += 1
        elif st in counts:
            counts[st] += 1
    return total, counts


def _annual_slot_violations(
    worker: Worker,
    total: int,
    counts: dict[str, int],
    limits: AnnualShiftLimitsConfig,
) -> list[ValidationViolationItem]:
    """年間上限と実績カウントを比較して違反リストを返す."""
    violations: list[ValidationViolationItem] = []

    if limits.annual_total > 0 and total > limits.annual_total:
        violations.append(
            ValidationViolationItem(
                code="ANNUAL_TOTAL_SHIFTS",
                severity="warning",
                message=(
                    f"{worker.name} の年間シフト回数が上限（{limits.annual_total}回）を超えています"
                    f"（現在: {total}回）"
                ),
                worker_ids=[str(worker.id)],
            )
        )

    slot_limit_map: list[tuple[str, str, int]] = [
        ("weekday_night", "ANNUAL_WEEKDAY_NIGHT", limits.weekday_night),
        ("sat_day", "ANNUAL_SAT_DAY", limits.sat_day),
        ("sat_night", "ANNUAL_SAT_NIGHT", limits.sat_night),
        ("sun_hol_day", "ANNUAL_SUN_HOL_DAY", limits.sun_hol_day),
        ("sun_hol_night", "ANNUAL_SUN_HOL_NIGHT", limits.sun_hol_night),
        ("sat_pre_hol_night", "ANNUAL_SAT_PRE_HOL_NIGHT", limits.sat_pre_hol_night),
    ]
    for st_key, code, limit in slot_limit_map:
        if limit > 0 and counts.get(st_key, 0) > limit:
            violations.append(
                ValidationViolationItem(
                    code=code,
                    severity="warning",
                    message=(
                        f"{worker.name} の{_SLOT_ANNUAL_LABEL[st_key]}年間シフト回数が"
                        f"上限（{limit}回）を超えています（現在: {counts[st_key]}回）"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )

    return violations


def _check_annual_shift_limits(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    limits: AnnualShiftLimitsConfig,
    employment_type_rules: dict[uuid.UUID, EmploymentTypeRuleConfig] | None = None,
    worker_custom_rules: dict[uuid.UUID, CustomRule | None] | None = None,
) -> list[ValidationViolationItem]:
    """年間シフト回数上限超過チェック.

    シフト日から遡って12ヶ月分（作成中の月を含む）のアサイン実績を集計し、
    各種別の上限を超えているワーカーを検出する。
    severity: "warning" として返す（保存はブロックしない）。

    long_hol_day / long_hol_night はそれぞれ sun_hol_day / sun_hol_night に合算して集計する。

    集計は2つのソースを組み合わせる:
    - ShiftRequirementAssignment: 当月の作成中アサイン（計画フロー）
    - WorkerMonthlySlotStats: 過去月の published プランデータ（インポートフロー）

    適用優先順位: カスタムルール > 雇用形態別ルール > グローバルルール。
    """
    import calendar as _calendar

    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    slot_type: SlotTypeEnum = SlotTypeEnum(str(requirement.slot_type))

    # 集計期間: シフト日が属する月を含む直近12ヶ月
    period_start_month = shift_date.month + 1
    period_start_year = shift_date.year - 1
    if period_start_month > 12:
        period_start_month -= 12
        period_start_year += 1
    period_start = date(period_start_year, period_start_month, 1)
    last_day = _calendar.monthrange(shift_date.year, shift_date.month)[1]
    period_end_inclusive = date(shift_date.year, shift_date.month, last_day)

    # 集計期間の年月文字列（WorkerMonthlySlotStats クエリ用）
    ym_start = f"{period_start.year:04d}-{period_start.month:02d}"
    ym_current = f"{shift_date.year:04d}-{shift_date.month:02d}"

    # 当月の開始日（ShiftRequirementAssignment は当月のみ対象）
    current_month_start = date(shift_date.year, shift_date.month, 1)

    violations: list[ValidationViolationItem] = []
    custom_rules = worker_custom_rules or {}

    for worker in workers:
        # --- 1. 当月のアサイン: ShiftRequirementAssignment を参照 ---
        req_rows = session.exec(
            select(ShiftRequirement.slot_type)
            .join(
                ShiftRequirementAssignment,
                ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirement.shift_date >= current_month_start,
                ShiftRequirement.shift_date <= period_end_inclusive,
            )
        ).all()

        # --- 2. 過去月のアサイン: WorkerMonthlySlotStats（published プラン）を参照 ---
        # WorkerMonthlySlotStats が存在する月を特定し、その月のカウントを取得する
        stats_rows = session.exec(
            select(
                WorkerMonthlySlotStats.year_month,
                WorkerMonthlySlotStats.slot_type,
                func.sum(WorkerMonthlySlotStats.count).label("total"),
            )
            .where(
                WorkerMonthlySlotStats.worker_id == worker.id,  # type: ignore[arg-type]
                WorkerMonthlySlotStats.tenant_id == tenant_id,
                WorkerMonthlySlotStats.year_month >= ym_start,
                WorkerMonthlySlotStats.year_month < ym_current,
            )
            .group_by(
                WorkerMonthlySlotStats.year_month,
                WorkerMonthlySlotStats.slot_type,
            )
        ).all()

        # published データが存在する年月セット（この月は ShiftRequirementAssignment を使わない）
        months_with_published: set[str] = {str(row[0]) for row in stats_rows}

        # --- 3. 過去月のアサイン（published がない月）: ShiftRequirementAssignment を参照 ---
        past_req_rows = session.exec(
            select(ShiftRequirement.shift_date, ShiftRequirement.slot_type)
            .join(
                ShiftRequirementAssignment,
                ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirement.shift_date >= period_start,
                ShiftRequirement.shift_date < current_month_start,
            )
        ).all()

        # published データがある月は ShiftRequirementAssignment を除外（二重カウント防止）
        past_req_slot_types = [
            str(row[1])
            for row in past_req_rows
            if f"{cast(date, row[0]).year:04d}-{cast(date, row[0]).month:02d}"
            not in months_with_published
        ]

        # published データを展開（count 分だけ slot_type を繰り返す）
        published_slot_types: list[str] = []
        for row in stats_rows:
            published_slot_types.extend([str(row[1])] * int(row[2]))

        slot_types = (
            [str(r) for r in req_rows]
            + past_req_slot_types
            + published_slot_types
            + [str(slot_type)]
        )
        total, counts = _count_annual_slots(slot_types)

        # 優先順位: カスタムルール > 雇用形態別 > グローバル の順で年間上限上書きを適用
        effective_limits = limits
        worker_id = cast(uuid.UUID, worker.id)
        custom_rule = custom_rules.get(worker_id)

        if custom_rule is not None and custom_rule.annual_limit_overrides is not None:
            # カスタムルールが最優先
            overrides_raw = custom_rule.annual_limit_overrides
            overrides = (
                AnnualPartialLimitsConfig(**overrides_raw)
                if isinstance(overrides_raw, dict)
                else None
            )
            if overrides is not None:
                effective_limits = AnnualShiftLimitsConfig(
                    annual_total=overrides.annual_total
                    if overrides.annual_total is not None
                    else limits.annual_total,
                    weekday_night=overrides.weekday_night
                    if overrides.weekday_night is not None
                    else limits.weekday_night,
                    sat_day=overrides.sat_day
                    if overrides.sat_day is not None
                    else limits.sat_day,
                    sat_night=overrides.sat_night
                    if overrides.sat_night is not None
                    else limits.sat_night,
                    sun_hol_day=overrides.sun_hol_day
                    if overrides.sun_hol_day is not None
                    else limits.sun_hol_day,
                    sun_hol_night=overrides.sun_hol_night
                    if overrides.sun_hol_night is not None
                    else limits.sun_hol_night,
                    sat_pre_hol_night=overrides.sat_pre_hol_night
                    if overrides.sat_pre_hol_night is not None
                    else limits.sat_pre_hol_night,
                )
        elif employment_type_rules and worker.employment_type_id is not None:
            # 雇用形態別ルールにフォールバック
            et_id = cast(uuid.UUID, worker.employment_type_id)
            et_rule = employment_type_rules.get(et_id)
            if et_rule is not None and et_rule.annual_limit_overrides is not None:
                overrides = et_rule.annual_limit_overrides
                effective_limits = AnnualShiftLimitsConfig(
                    annual_total=overrides.annual_total
                    if overrides.annual_total is not None
                    else limits.annual_total,
                    weekday_night=overrides.weekday_night
                    if overrides.weekday_night is not None
                    else limits.weekday_night,
                    sat_day=overrides.sat_day
                    if overrides.sat_day is not None
                    else limits.sat_day,
                    sat_night=overrides.sat_night
                    if overrides.sat_night is not None
                    else limits.sat_night,
                    sun_hol_day=overrides.sun_hol_day
                    if overrides.sun_hol_day is not None
                    else limits.sun_hol_day,
                    sun_hol_night=overrides.sun_hol_night
                    if overrides.sun_hol_night is not None
                    else limits.sun_hol_night,
                    sat_pre_hol_night=overrides.sat_pre_hol_night
                    if overrides.sat_pre_hol_night is not None
                    else limits.sat_pre_hol_night,
                )

        violations.extend(
            _annual_slot_violations(worker, total, counts, effective_limits)
        )

    return violations


_NON_WEEKDAY_NIGHT_SLOT_TYPES: frozenset[str] = frozenset(
    [
        SlotTypeEnum.sat_day,
        SlotTypeEnum.sat_night,
        SlotTypeEnum.sun_hol_day,
        SlotTypeEnum.sun_hol_night,
        SlotTypeEnum.long_hol_day,
        SlotTypeEnum.long_hol_night,
        SlotTypeEnum.sat_pre_hol_night,
    ]
)


def _check_total_age_limit(
    workers: list[Worker],
    rules: ShiftRulesConfig,
    shift_date: date,
) -> list[ValidationViolationItem]:
    """合計年齢上限チェック.

    スロット内にアサインされるワーカーの年齢合計が ``rules.max_total_age`` を超える場合にエラーを返す。
    ``max_total_age`` が 0 の場合は制限なし。
    ``birth_date`` が null のワーカーは計算から除外（0歳扱い）。
    ワーカーが0人の場合はスキップ。
    """
    if rules.max_total_age == 0:
        return []
    if not workers:
        return []

    reference_date = shift_date.replace(day=1)
    workers_with_birth_date = [w for w in workers if w.birth_date is not None]
    age_sum = sum(
        calculate_age_at(cast(date, w.birth_date), reference_date)
        for w in workers_with_birth_date
    )

    if age_sum <= rules.max_total_age:
        return []

    return [
        ValidationViolationItem(
            code="TOTAL_AGE_LIMIT",
            severity="error",
            message=(
                f"スロット内ワーカーの年齢合計が上限（{rules.max_total_age}歳）を超えています"
                f"（合計: {age_sum}歳）"
            ),
            worker_ids=[str(w.id) for w in workers_with_birth_date],
        )
    ]


def _get_month_range(shift_date: date) -> tuple[date, date]:
    """シフト日が属する月の開始日・終了日を返す."""
    import calendar

    month_start = shift_date.replace(day=1)
    last_day = calendar.monthrange(shift_date.year, shift_date.month)[1]
    month_end = shift_date.replace(day=last_day)
    return month_start, month_end


def _count_monthly_assignments(
    session: Session,
    tenant_id: str,
    worker_id: object,
    month_start: date,
    month_end: date,
    slot_types: list[str] | None,
    exclude_requirement_id: object,
) -> int:
    """指定期間・スロット種別の月間アサイン数をカウントする.

    Args:
        slot_types: 対象スロット種別リスト。None の場合は全スロットを対象とする。
        exclude_requirement_id: 除外する requirement_id（現在のアサイン対象）。
    """
    stmt = (
        select(ShiftRequirementAssignment)
        .join(
            ShiftRequirement,
            ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
        )
        .where(
            ShiftRequirementAssignment.worker_id == worker_id,
            ShiftRequirementAssignment.tenant_id == tenant_id,
            ShiftRequirement.shift_date >= month_start,
            ShiftRequirement.shift_date <= month_end,
            ShiftRequirementAssignment.requirement_id != exclude_requirement_id,  # type: ignore[arg-type]
        )
    )
    if slot_types is not None:
        stmt = stmt.where(ShiftRequirement.slot_type.in_(slot_types))  # type: ignore[union-attr]
    return len(session.exec(stmt).all())


def _check_non_weekday_night_limit(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """平日夜間以外シフト回数上限チェック（NON_WEEKDAY_NIGHT_LIMIT）.

    対象スロットが平日夜間以外（``weekday_night`` 以外）のとき、
    同一月内で各ワーカーがすでに
    ``monthly_shift_limits.non_weekday_night`` 回以上の平日夜間以外スロットに
    アサインされている場合にエラーを返す。
    ``non_weekday_night`` が 0 の場合は制限なし。
    """
    limit = rules.monthly_shift_limits.non_weekday_night
    if limit == 0:
        return []

    slot_type_str = str(requirement.slot_type)
    if slot_type_str not in _NON_WEEKDAY_NIGHT_SLOT_TYPES:
        return []

    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    month_start, month_end = _get_month_range(shift_date)

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        count = _count_monthly_assignments(
            session,
            tenant_id,
            worker.id,
            month_start,
            month_end,
            list(_NON_WEEKDAY_NIGHT_SLOT_TYPES),
            requirement.id,
        )
        # 今回のアサイン分を含めてカウント
        if count + 1 > limit:
            violations.append(
                ValidationViolationItem(
                    code="NON_WEEKDAY_NIGHT_LIMIT",
                    severity="error",
                    message=(
                        f"{worker.name} は今月の平日夜間以外シフト回数が"
                        f"上限（{limit}回）を超えています"
                        f"（現在: {count + 1}回）"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def _check_monthly_total_limit(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """月間総シフト回数上限チェック（MONTHLY_TOTAL_LIMIT）.

    同一月内で各ワーカーの全スロット合計アサイン回数が
    ``monthly_shift_limits.monthly_total`` を超える場合にエラーを返す。
    ``monthly_total`` が 0 の場合は制限なし。
    """
    limit = rules.monthly_shift_limits.monthly_total
    if limit == 0:
        return []

    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    month_start, month_end = _get_month_range(shift_date)

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        count = _count_monthly_assignments(
            session,
            tenant_id,
            worker.id,
            month_start,
            month_end,
            None,  # 全スロット種別対象
            requirement.id,
        )
        if count + 1 > limit:
            violations.append(
                ValidationViolationItem(
                    code="MONTHLY_TOTAL_LIMIT",
                    severity="error",
                    message=(
                        f"{worker.name} は今月の総シフト回数が"
                        f"上限（{limit}回）を超えています"
                        f"（現在: {count + 1}回）"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def _check_monthly_weekday_night_limit(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """月間平日夜間シフト回数上限チェック（MONTHLY_WEEKDAY_NIGHT_LIMIT）.

    対象スロットが weekday_night のとき、同一月内で各ワーカーの
    weekday_night アサイン回数が ``monthly_shift_limits.weekday_night`` を超える場合にエラーを返す。
    ``weekday_night`` が 0 の場合は制限なし。
    """
    limit = rules.monthly_shift_limits.weekday_night
    if limit == 0:
        return []

    slot_type_str = str(requirement.slot_type)
    if slot_type_str != str(SlotTypeEnum.weekday_night):
        return []

    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    month_start, month_end = _get_month_range(shift_date)

    violations: list[ValidationViolationItem] = []
    for worker in workers:
        count = _count_monthly_assignments(
            session,
            tenant_id,
            worker.id,
            month_start,
            month_end,
            [str(SlotTypeEnum.weekday_night)],
            requirement.id,
        )
        if count + 1 > limit:
            violations.append(
                ValidationViolationItem(
                    code="MONTHLY_WEEKDAY_NIGHT_LIMIT",
                    severity="error",
                    message=(
                        f"{worker.name} は今月の平日夜間シフト回数が"
                        f"上限（{limit}回）を超えています"
                        f"（現在: {count + 1}回）"
                    ),
                    worker_ids=[str(worker.id)],
                )
            )
    return violations


def validate_shift_assignments(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
    annual_limits: AnnualShiftLimitsConfig | None = None,
) -> list[ValidationViolationItem]:
    """指定されたシフトアサインがビジネスルールに適合しているか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        requirement: アサイン対象のShiftRequirementオブジェクト。
        workers: アサイン対象のWorkerオブジェクトリスト。
        rules: 適用するシフトルール設定。
        annual_limits: 年間シフト回数上限設定。None の場合はデフォルト値を使用。

    Returns:
        バリデーション違反アイテムのリスト。空の場合は違反なし。
    """
    if not workers:
        return []

    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    limits = annual_limits if annual_limits is not None else AnnualShiftLimitsConfig()

    non_default_et_ids = _load_non_default_employment_type_ids(session, tenant_id)
    et_rules = _load_employment_type_rules(session, tenant_id)
    worker_custom_rule_map = _load_worker_custom_rule_objects(
        session, tenant_id, workers
    )

    return [
        *_check_daily_duplicate(session, tenant_id, requirement, workers),
        *_check_same_department(workers, rules),
        *_check_skill_rank(session, requirement, workers, rules),
        *_check_work_interval(session, tenant_id, requirement, workers, rules),
        *_check_assign_prohibited(workers, worker_custom_rule_map),
        *_check_special_employment(
            requirement,
            workers,
            rules,
            non_default_et_ids,
            et_rules,
            worker_custom_rule_map,
        ),
        *_check_employment_pair_restriction(
            requirement, workers, rules, non_default_et_ids, et_rules
        ),
        *_check_age_restriction(workers, shift_date),
        *_check_position_exclusion(session, tenant_id, requirement, workers),
        *_check_tenure_restriction(workers, shift_date, rules),
        *_check_sun_hol_day_monthly_limit(session, tenant_id, requirement, workers),
        *_check_long_holiday_prev_year_exclusion(
            session, tenant_id, requirement, workers
        ),
        *_check_annual_shift_limits(
            session,
            tenant_id,
            requirement,
            workers,
            limits,
            et_rules,
            worker_custom_rule_map,
        ),
        *_check_total_age_limit(workers, rules, shift_date),
        *_check_non_weekday_night_limit(
            session, tenant_id, requirement, workers, rules
        ),
        *_check_monthly_total_limit(session, tenant_id, requirement, workers, rules),
        *_check_monthly_weekday_night_limit(
            session, tenant_id, requirement, workers, rules
        ),
    ]
