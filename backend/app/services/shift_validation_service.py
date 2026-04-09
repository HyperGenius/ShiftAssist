# backend/app/services/shift_validation_service.py
"""シフトアサインのビジネスルール検証サービス層.

``shift_rules_service`` が提供するルール定義に基づいて、
シフトアサインの妥当性を検証する純粋なバリデーターを提供する。
"""

import uuid
from datetime import date
from typing import cast

from sqlmodel import Session, select

from app.models.models import (
    LongHolidayPeriod,
    LongHolidayTypeEnum,
    Position,
    ShiftRequirement,
    ShiftRequirementAssignment,
    SlotTypeEnum,
    TenantSkillRank,
    Worker,
)
from app.models.rule_schemas import ShiftRulesConfig, ValidationViolationItem
from app.services.age_utils import calculate_age_at
from app.services.long_holiday_period_service import (
    get_period_for_date,
    is_holiday_type_excluded_by_position,
)


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
    """ルール4: 中N日以上の勤務間隔チェック."""
    violations: list[ValidationViolationItem] = []
    for worker in workers:
        other_req_ids = session.exec(
            select(ShiftRequirementAssignment.requirement_id).where(  # type: ignore[arg-type]
                ShiftRequirementAssignment.worker_id == worker.id,
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirementAssignment.requirement_id != requirement.id,  # type: ignore[arg-type]
            )
        ).all()
        if not other_req_ids:
            continue
        other_reqs = session.exec(
            select(ShiftRequirement).where(
                ShiftRequirement.id.in_(other_req_ids),  # type: ignore[attr-defined]
                ShiftRequirement.tenant_id == tenant_id,
            )
        ).all()
        for other_req in other_reqs:
            shift_date: date = requirement.shift_date  # type: ignore[assignment]
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
                break
    return violations


def _check_special_employment(
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """ルール5: 特別雇用者の枠制限チェック."""
    allowed_slots = set(rules.special_employment_shifts)
    if str(requirement.slot_type) in allowed_slots:
        return []
    allowed_slots_str = "、".join(rules.special_employment_shifts)
    violations: list[ValidationViolationItem] = []
    for worker in workers:
        if worker.is_special:
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
    """ルール7: 役職除外チェック（長期休暇期間中の除外フラグを持つ役職のアサイン禁止）."""
    shift_date: date = requirement.shift_date  # type: ignore[assignment]
    period = get_period_for_date(session, tenant_id, shift_date)
    if period is None:
        return []

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
        if is_holiday_type_excluded_by_position(period.holiday_type, position):  # type: ignore[arg-type]
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


def validate_shift_assignments(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """指定されたシフトアサインがビジネスルールに適合しているか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        requirement: アサイン対象のShiftRequirementオブジェクト。
        workers: アサイン対象のWorkerオブジェクトリスト。
        rules: 適用するシフトルール設定。

    Returns:
        バリデーション違反アイテムのリスト。空の場合は違反なし。
    """
    if not workers:
        return []

    shift_date: date = requirement.shift_date  # type: ignore[assignment]

    return [
        *_check_daily_duplicate(session, tenant_id, requirement, workers),
        *_check_same_department(workers, rules),
        *_check_skill_rank(session, requirement, workers, rules),
        *_check_work_interval(session, tenant_id, requirement, workers, rules),
        *_check_special_employment(requirement, workers, rules),
        *_check_age_restriction(workers, shift_date),
        *_check_position_exclusion(session, tenant_id, requirement, workers),
        *_check_tenure_restriction(workers, shift_date, rules),
        *_check_sun_hol_day_monthly_limit(session, tenant_id, requirement, workers),
        *_check_long_holiday_prev_year_exclusion(
            session, tenant_id, requirement, workers
        ),
    ]
