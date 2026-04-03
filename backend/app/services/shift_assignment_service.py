# backend/app/services/shift_assignment_service.py
"""ShiftRequirementAssignment CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import (
    Department,
    ShiftRequirement,
    ShiftRequirementAssignment,
    Worker,
)
from app.models.schemas import ShiftAssignmentsSave, WorkerAssignmentItem
from app.services import shift_rules_service, shift_validation_service


def _validate_requirement(
    session: Session, tenant_id: str, requirement_id: uuid.UUID
) -> ShiftRequirement:
    """指定された ``requirement_id`` が同一テナントに存在するか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        requirement_id: 検証対象のShiftRequirement ID。

    Returns:
        検証済みのShiftRequirementオブジェクト。

    Raises:
        HTTPException: ShiftRequirementが存在しない、または異なるテナントに属する場合。
    """
    req = session.exec(
        select(ShiftRequirement).where(
            ShiftRequirement.id == requirement_id,  # type: ignore[arg-type]
            ShiftRequirement.tenant_id == tenant_id,
        )
    ).first()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShiftRequirement '{requirement_id}' not found in tenant.",
        )
    return req


def _validate_workers(
    session: Session, tenant_id: str, worker_ids: list[uuid.UUID]
) -> None:
    """指定されたすべてのワーカーIDが同一テナントに存在するか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        worker_ids: 検証対象のワーカーIDリスト。

    Raises:
        HTTPException: いずれかのワーカーが存在しない、または異なるテナントに属する場合。
    """
    if not worker_ids:
        return
    workers = session.exec(
        select(Worker).where(
            Worker.id.in_(worker_ids),  # type: ignore[attr-defined]
            Worker.tenant_id == tenant_id,
        )
    ).all()
    found_ids = {w.id for w in workers}
    missing = [wid for wid in worker_ids if wid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workers not found in tenant: {missing}",
        )


def _validate_worker_departments(
    session: Session,
    tenant_id: str,
    worker_ids: list[uuid.UUID],
) -> None:
    """ワーカーがテナント設定のシフト対象部門に属しているかを検証する.

    ``target_all_departments`` が True の場合は検証をスキップする。
    ワーカーが対象外の部門に属している場合は 400 Bad Request を送出する。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        worker_ids: 検証対象のワーカーIDリスト。

    Raises:
        HTTPException: ワーカーがシフト対象部門外の部門に属している場合（400）。
    """
    if not worker_ids:
        return

    rules = shift_rules_service.get_shift_rules(session, tenant_id).shift_rules

    if rules.target_all_departments:
        return

    if not rules.target_departments:
        return

    workers = list(
        session.exec(
            select(Worker).where(
                Worker.id.in_(worker_ids),  # type: ignore[attr-defined]
                Worker.tenant_id == tenant_id,
            )
        ).all()
    )

    dept_ids = list({w.department_id for w in workers})
    departments = list(
        session.exec(
            select(Department).where(
                Department.id.in_(dept_ids),  # type: ignore[attr-defined]
                Department.tenant_id == tenant_id,
            )
        ).all()
    )

    allowed_codes = set(rules.target_departments)
    disallowed = [dept for dept in departments if dept.code not in allowed_codes]
    if disallowed:
        names = [str(d.name) for d in disallowed]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"以下の部門はシフト対象部門として設定されていません: {', '.join(names)}",
        )


def _validate_business_rules(
    session: Session,
    tenant_id: str,
    requirement: ShiftRequirement,
    worker_ids: list[uuid.UUID],
) -> None:
    """アサイン対象ワーカーに対してビジネスルール検証を実行する.

    違反がある場合は 400 Bad Request を送出する。
    worker_ids が空の場合は検証をスキップする。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        requirement: アサイン対象のShiftRequirement。
        worker_ids: アサイン対象のワーカーIDリスト。

    Raises:
        HTTPException: ビジネスルール違反が検出された場合（400）。
    """
    if not worker_ids:
        return

    workers = list(
        session.exec(
            select(Worker).where(
                Worker.id.in_(worker_ids),  # type: ignore[attr-defined]
                Worker.tenant_id == tenant_id,
            )
        ).all()
    )

    rules = shift_rules_service.get_shift_rules(session, tenant_id).shift_rules
    violations = shift_validation_service.validate_shift_assignments(
        session, tenant_id, requirement, workers, rules
    )
    errors = [v for v in violations if v.severity == "error"]
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "シフトルール違反があります。"
                    "is_manual_override を true に設定するか、アサインを修正してください。"
                ),
                "violations": [v.model_dump() for v in errors],
            },
        )


def upsert_assignments(
    session: Session,
    tenant_id: str,
    requirement_id: uuid.UUID,
    data: ShiftAssignmentsSave,
) -> list[WorkerAssignmentItem]:
    """指定したShiftRequirementのアサイン情報を上書き保存する.

    既存のアサイン情報をすべて削除してから新しい情報を追加する。
    ``data.worker_ids`` が空の場合、アサインを全削除して空リストを返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        requirement_id: 対象ShiftRequirement ID。
        data: アサイン保存リクエストデータ。

    Returns:
        保存後のアサイン一覧。

    Raises:
        HTTPException: ShiftRequirementまたはWorkerが存在しない、または異なるテナントに属する場合。
    """
    req = _validate_requirement(session, tenant_id, requirement_id)
    _validate_workers(session, tenant_id, data.worker_ids)
    _validate_worker_departments(session, tenant_id, data.worker_ids)

    if not data.is_manual_override:
        _validate_business_rules(session, tenant_id, req, data.worker_ids)

    # 既存のアサインを全削除
    existing = session.exec(
        select(ShiftRequirementAssignment).where(
            ShiftRequirementAssignment.requirement_id == requirement_id,  # type: ignore[arg-type]
            ShiftRequirementAssignment.tenant_id == tenant_id,
        )
    ).all()
    for assignment in existing:
        session.delete(assignment)

    # 新しいアサインを追加
    new_assignments: list[ShiftRequirementAssignment] = []
    for worker_id in data.worker_ids:
        assignment = ShiftRequirementAssignment(
            tenant_id=tenant_id,
            requirement_id=requirement_id,
            worker_id=worker_id,
            is_manual_override=data.is_manual_override,
        )
        session.add(assignment)
        new_assignments.append(assignment)

    session.commit()
    for assignment in new_assignments:
        session.refresh(assignment)

    return [WorkerAssignmentItem.model_validate(a) for a in new_assignments]


def list_assignments_for_requirement(
    session: Session,
    tenant_id: str,
    requirement_id: uuid.UUID,
) -> list[WorkerAssignmentItem]:
    """指定したShiftRequirementのアサイン一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        requirement_id: 対象ShiftRequirement ID。

    Returns:
        アサイン一覧。
    """
    _validate_requirement(session, tenant_id, requirement_id)
    assignments = session.exec(
        select(ShiftRequirementAssignment).where(
            ShiftRequirementAssignment.requirement_id == requirement_id,  # type: ignore[arg-type]
            ShiftRequirementAssignment.tenant_id == tenant_id,
        )
    ).all()
    return [WorkerAssignmentItem.model_validate(a) for a in assignments]
