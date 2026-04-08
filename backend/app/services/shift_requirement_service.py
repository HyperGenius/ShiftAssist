# backend/app/services/shift_requirement_service.py
"""ShiftRequirement CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import calendar
import uuid
from collections import defaultdict
from datetime import date
from typing import cast

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import Department, ShiftRequirement, ShiftRequirementAssignment
from app.models.schemas import (
    ShiftReqCreate,
    ShiftReqResponse,
    ShiftReqUpdate,
    WorkerAssignmentItem,
)


def _validate_department(
    session: Session, tenant_id: str, department_id: uuid.UUID
) -> None:
    """指定された ``department_id`` が同一テナントに存在するか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        department_id: 検証対象の部門ID。

    Raises:
        HTTPException: 部門が存在しない、または異なるテナントに属する場合。
    """
    dept = session.exec(
        select(Department).where(
            Department.id == department_id,  # type: ignore[arg-type]
            Department.tenant_id == tenant_id,
        )
    ).first()
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{department_id}' not found in tenant.",
        )


def _validate_date_not_past(target_date: date) -> None:
    """指定された日付が過去日でないことを検証する.

    Args:
        target_date: 検証対象の日付。

    Raises:
        HTTPException: 指定した日付が過去の場合。
    """
    if target_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="過去の日付に対するシフト枠の作成・変更はできません。",
        )


def create_shift_req(
    session: Session, tenant_id: str, data: ShiftReqCreate
) -> ShiftReqResponse:
    """新しいShiftRequirementを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: ShiftRequirement作成リクエストデータ。

    Returns:
        作成されたShiftRequirementのレスポンスモデル。

    Raises:
        HTTPException: ``department_id`` が同一テナントに存在しない場合、
            または指定日付が過去の場合。
    """
    _validate_date_not_past(data.shift_date)
    _validate_department(session, tenant_id, data.department_id)

    req = ShiftRequirement(
        tenant_id=tenant_id,
        department_id=data.department_id,
        shift_date=data.shift_date,
        slot_type=data.slot_type,
        required_headcount=data.required_headcount,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return ShiftReqResponse.model_validate(req)


def list_shift_reqs(
    session: Session,
    tenant_id: str,
    year: int | None = None,
    month: int | None = None,
) -> list[ShiftReqResponse]:
    """テナントに属するShiftRequirement一覧を取得する.

    アサイン情報も含めて返す。
    year と month を指定した場合は、対象年月のデータのみを返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        year: フィルタリングする年（month と合わせて指定）。
        month: フィルタリングする月（year と合わせて指定）。

    Returns:
        ShiftRequirement一覧のレスポンスモデルリスト（アサイン情報含む）。
    """
    stmt = select(ShiftRequirement).where(ShiftRequirement.tenant_id == tenant_id)
    if year is not None and month is not None:
        month_start = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_end = date(year, month, last_day)
        stmt = stmt.where(
            ShiftRequirement.shift_date >= month_start,  # type: ignore[operator]  # SQLModelのdateカラムの比較演算子はランタイムで正常動作するが型定義が不完全なため抑制
            ShiftRequirement.shift_date <= month_end,  # type: ignore[operator]  # 同上
        )
    reqs = session.exec(stmt).all()

    if not reqs:
        return []

    req_ids = [r.id for r in reqs]
    all_assignments = session.exec(
        select(ShiftRequirementAssignment).where(
            ShiftRequirementAssignment.requirement_id.in_(req_ids),  # type: ignore[attr-defined]
            ShiftRequirementAssignment.tenant_id == tenant_id,
        )
    ).all()

    assignments_by_req: dict[uuid.UUID, list[WorkerAssignmentItem]] = defaultdict(list)
    for a in all_assignments:
        assignments_by_req[cast(uuid.UUID, a.requirement_id)].append(
            WorkerAssignmentItem.model_validate(a)
        )

    result = []
    for r in reqs:
        resp = ShiftReqResponse.model_validate(r)
        resp.assignments = assignments_by_req.get(cast(uuid.UUID, r.id), [])
        result.append(resp)
    return result


def get_shift_req(
    session: Session, tenant_id: str, req_id: uuid.UUID
) -> ShiftReqResponse:
    """指定したShiftRequirementを取得する.

    アサイン情報も含めて返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        req_id: 取得対象のShiftRequirement ID。

    Returns:
        ShiftRequirementレスポンスモデル（アサイン情報含む）。

    Raises:
        HTTPException: ShiftRequirementが存在しない、または異なるテナントに属する場合。
    """
    req = session.exec(
        select(ShiftRequirement).where(
            ShiftRequirement.id == req_id,  # type: ignore[arg-type]
            ShiftRequirement.tenant_id == tenant_id,
        )
    ).first()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShiftRequirement '{req_id}' not found.",
        )
    assignments = session.exec(
        select(ShiftRequirementAssignment).where(
            ShiftRequirementAssignment.requirement_id == req_id,  # type: ignore[arg-type]
            ShiftRequirementAssignment.tenant_id == tenant_id,
        )
    ).all()
    resp = ShiftReqResponse.model_validate(req)
    resp.assignments = [WorkerAssignmentItem.model_validate(a) for a in assignments]
    return resp


def update_shift_req(
    session: Session,
    tenant_id: str,
    req_id: uuid.UUID,
    data: ShiftReqUpdate,
) -> ShiftReqResponse:
    """指定したShiftRequirementを更新する.

    ``model_dump(exclude_unset=True)`` により、指定されたフィールドのみを更新する。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        req_id: 更新対象のShiftRequirement ID。
        data: ShiftRequirement更新リクエストデータ。

    Returns:
        更新後のShiftRequirementレスポンスモデル。

    Raises:
        HTTPException: ShiftRequirementが存在しない場合、``department_id`` が
            同一テナントに存在しない場合、または指定日付が過去の場合。
    """
    req = session.exec(
        select(ShiftRequirement).where(
            ShiftRequirement.id == req_id,  # type: ignore[arg-type]
            ShiftRequirement.tenant_id == tenant_id,
        )
    ).first()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShiftRequirement '{req_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "shift_date" in update_data:
        _validate_date_not_past(update_data["shift_date"])

    if "department_id" in update_data:
        _validate_department(session, tenant_id, update_data["department_id"])

    for field, value in update_data.items():
        setattr(req, field, value)

    session.add(req)
    session.commit()
    session.refresh(req)
    return ShiftReqResponse.model_validate(req)


def delete_shift_req(session: Session, tenant_id: str, req_id: uuid.UUID) -> None:
    """指定したShiftRequirementを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        req_id: 削除対象のShiftRequirement ID。

    Raises:
        HTTPException: ShiftRequirementが存在しない、または異なるテナントに属する場合。
    """
    req = session.exec(
        select(ShiftRequirement).where(
            ShiftRequirement.id == req_id,  # type: ignore[arg-type]
            ShiftRequirement.tenant_id == tenant_id,
        )
    ).first()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShiftRequirement '{req_id}' not found.",
        )
    session.delete(req)
    session.commit()
