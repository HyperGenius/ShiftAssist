# backend/app/services/position_service.py
"""Position CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import Position
from app.models.schemas import PositionCreate, PositionResponse, PositionUpdate


def create_position(
    session: Session, tenant_id: str, data: PositionCreate
) -> PositionResponse:
    """新しいPositionを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: Position作成リクエストデータ。

    Returns:
        作成されたPositionのレスポンスモデル。
    """
    position = Position(
        tenant_id=tenant_id,
        name=data.name,
        is_excluded_from_gw=data.is_excluded_from_gw,
        is_excluded_from_sw=data.is_excluded_from_sw,
        is_excluded_from_year_end=data.is_excluded_from_year_end,
        is_excluded_from_all_shifts=data.is_excluded_from_all_shifts,
    )
    session.add(position)
    session.commit()
    session.refresh(position)
    return PositionResponse.model_validate(position)


def list_positions(session: Session, tenant_id: str) -> list[PositionResponse]:
    """テナントに属するPosition一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        Position一覧のレスポンスモデルリスト。
    """
    positions = session.exec(
        select(Position).where(Position.tenant_id == tenant_id)
    ).all()
    return [PositionResponse.model_validate(p) for p in positions]


def get_position(
    session: Session, tenant_id: str, position_id: uuid.UUID
) -> PositionResponse:
    """指定したPositionを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        position_id: 取得対象のPosition ID。

    Returns:
        Positionレスポンスモデル。

    Raises:
        HTTPException: Positionが存在しない場合。
    """
    position = session.exec(
        select(Position).where(
            Position.id == position_id,  # type: ignore[arg-type]
            Position.tenant_id == tenant_id,
        )
    ).first()
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position '{position_id}' not found.",
        )
    return PositionResponse.model_validate(position)


def update_position(
    session: Session,
    tenant_id: str,
    position_id: uuid.UUID,
    data: PositionUpdate,
) -> PositionResponse:
    """指定したPositionを更新する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        position_id: 更新対象のPosition ID。
        data: Position更新リクエストデータ。

    Returns:
        更新後のPositionレスポンスモデル。

    Raises:
        HTTPException: Positionが存在しない場合。
    """
    position = session.exec(
        select(Position).where(
            Position.id == position_id,  # type: ignore[arg-type]
            Position.tenant_id == tenant_id,
        )
    ).first()
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position '{position_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(position, field, value)

    session.add(position)
    session.commit()
    session.refresh(position)
    return PositionResponse.model_validate(position)


def delete_position(session: Session, tenant_id: str, position_id: uuid.UUID) -> None:
    """指定したPositionを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        position_id: 削除対象のPosition ID。

    Raises:
        HTTPException: Positionが存在しない場合。
    """
    position = session.exec(
        select(Position).where(
            Position.id == position_id,  # type: ignore[arg-type]
            Position.tenant_id == tenant_id,
        )
    ).first()
    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position '{position_id}' not found.",
        )
    session.delete(position)
    session.commit()
