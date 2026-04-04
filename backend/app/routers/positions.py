# backend/app/routers/positions.py
"""Position CRUDルーター.

ベースパス: ``/api/positions``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import PositionCreate, PositionResponse, PositionUpdate
from app.services import position_service

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("/", response_model=list[PositionResponse])
def list_positions(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[PositionResponse]:
    """テナントに属するPosition一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Position一覧。
    """
    return position_service.list_positions(session, tenant_id)


@router.post("/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    data: PositionCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> PositionResponse:
    """新しいPositionを作成する.

    Args:
        data: Position作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたPositionの情報。
    """
    return position_service.create_position(session, tenant_id, data)


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(
    position_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> PositionResponse:
    """指定したPositionを取得する.

    Args:
        position_id: 取得対象のPosition ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Positionの情報。
    """
    return position_service.get_position(session, tenant_id, position_id)


@router.put("/{position_id}", response_model=PositionResponse)
def update_position(
    position_id: uuid.UUID,
    data: PositionUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> PositionResponse:
    """指定したPositionを更新する.

    Args:
        position_id: 更新対象のPosition ID。
        data: Position更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のPositionの情報。
    """
    return position_service.update_position(session, tenant_id, position_id, data)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したPositionを物理削除する.

    Args:
        position_id: 削除対象のPosition ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    position_service.delete_position(session, tenant_id, position_id)
