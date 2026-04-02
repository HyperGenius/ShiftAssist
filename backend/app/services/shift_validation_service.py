# backend/app/services/shift_validation_service.py
"""シフトアサインのビジネスルール検証サービス層.

``shift_rules_service`` が提供するルール定義に基づいて、
シフトアサインの妥当性を検証する純粋なバリデーターを提供する。
"""

import uuid
from datetime import date

from sqlmodel import Session, select

from app.models.models import ShiftRequirement, ShiftRequirementAssignment, Worker
from app.models.rule_schemas import ShiftRulesConfig, ValidationViolationItem


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
        seen_dept.add(w.department_id)
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
    requirement: ShiftRequirement,
    workers: list[Worker],
    rules: ShiftRulesConfig,
) -> list[ValidationViolationItem]:
    """ルール3: スキルランク必須チェック（全員アサイン済みの場合のみ）."""
    if len(workers) < requirement.required_headcount:
        return []
    if not rules.require_skill_ranks:
        return []
    worker_ranks = {str(w.skill_rank) for w in workers}
    required_ranks = set(rules.require_skill_ranks)
    if required_ranks.intersection(worker_ranks):
        return []
    return [
        ValidationViolationItem(
            code="SKILL_RANK_A",
            severity="error",
            message=(
                f"必須スキルランク（{', '.join(rules.require_skill_ranks)}）の"
                "メンバーが含まれていません"
            ),
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

    return [
        *_check_daily_duplicate(session, tenant_id, requirement, workers),
        *_check_same_department(workers, rules),
        *_check_skill_rank(requirement, workers, rules),
        *_check_work_interval(session, tenant_id, requirement, workers, rules),
        *_check_special_employment(requirement, workers, rules),
    ]

