# backend/app/routers/shift_requirements.py
"""ShiftRequirement CRUDルーター.

ベースパス: ``/api/shift-requirements``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    ShiftAssignmentsSave,
    ShiftReqCreate,
    ShiftReqResponse,
    ShiftReqUpdate,
    WorkerAssignmentItem,
)
from app.services import shift_assignment_service, shift_requirement_service

router = APIRouter(prefix="/api/shift-requirements", tags=["shift-requirements"])


@router.post("/", response_model=ShiftReqResponse, status_code=status.HTTP_201_CREATED)
def create_shift_req(
    data: ShiftReqCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftReqResponse:
    """新しいShiftRequirementを作成する.

    Args:
        data: ShiftRequirement作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたShiftRequirementの情報。
    """
    return shift_requirement_service.create_shift_req(session, tenant_id, data)


@router.get("/", response_model=list[ShiftReqResponse])
def list_shift_reqs(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[ShiftReqResponse]:
    """テナントに属するShiftRequirement一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        ShiftRequirement一覧。
    """
    return shift_requirement_service.list_shift_reqs(session, tenant_id)


@router.get("/{req_id}", response_model=ShiftReqResponse)
def get_shift_req(
    req_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftReqResponse:
    """指定したShiftRequirementを取得する.

    Args:
        req_id: 取得対象のShiftRequirement ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        ShiftRequirementの情報。
    """
    return shift_requirement_service.get_shift_req(session, tenant_id, req_id)


@router.put("/{req_id}", response_model=ShiftReqResponse)
def update_shift_req(
    req_id: uuid.UUID,
    data: ShiftReqUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftReqResponse:
    """指定したShiftRequirementを更新する.

    Args:
        req_id: 更新対象のShiftRequirement ID。
        data: ShiftRequirement更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のShiftRequirementの情報。
    """
    return shift_requirement_service.update_shift_req(session, tenant_id, req_id, data)


@router.delete("/{req_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift_req(
    req_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したShiftRequirementを物理削除する.

    Args:
        req_id: 削除対象のShiftRequirement ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    shift_requirement_service.delete_shift_req(session, tenant_id, req_id)


@router.put(
    "/{req_id}/assignments",
    response_model=list[WorkerAssignmentItem],
)
def upsert_shift_req_assignments(
    req_id: uuid.UUID,
    data: ShiftAssignmentsSave,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[WorkerAssignmentItem]:
    """指定したShiftRequirementのアサイン情報を上書き保存する.

    既存のアサイン情報をすべて削除してから新しい情報を追加する。
    ``is_manual_override`` が ``True`` の場合、ルール違反を承知の上での強制保存となる。

    Args:
        req_id: 対象のShiftRequirement ID。
        data: アサイン保存リクエストボディ（worker_ids, is_manual_override）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        保存後のアサイン一覧。
    """
    return shift_assignment_service.upsert_assignments(session, tenant_id, req_id, data)
