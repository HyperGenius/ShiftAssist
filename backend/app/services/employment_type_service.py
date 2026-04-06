# backend/app/services/employment_type_service.py
"""EmploymentType CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import EmploymentType
from app.models.schemas import (
    EmploymentTypeCreate,
    EmploymentTypeResponse,
    EmploymentTypeUpdate,
)


def create_employment_type(
    session: Session, tenant_id: str, data: EmploymentTypeCreate
) -> EmploymentTypeResponse:
    """新しいEmploymentTypeを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: EmploymentType作成リクエストデータ。

    Returns:
        作成されたEmploymentTypeのレスポンスモデル。

    Raises:
        HTTPException: 同テナント内で同名の雇用形態が既に存在する場合。
    """
    existing = session.exec(
        select(EmploymentType).where(
            EmploymentType.tenant_id == tenant_id,
            EmploymentType.name == data.name,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"EmploymentType '{data.name}' already exists.",
        )

    employment_type = EmploymentType(
        tenant_id=tenant_id,
        name=data.name,
    )
    session.add(employment_type)
    session.commit()
    session.refresh(employment_type)
    return EmploymentTypeResponse.model_validate(employment_type)


def list_employment_types(
    session: Session, tenant_id: str
) -> list[EmploymentTypeResponse]:
    """テナントに属するEmploymentType一覧を取得する（名前昇順）.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        EmploymentType一覧のレスポンスモデルリスト。
    """
    employment_types = session.exec(
        select(EmploymentType)
        .where(EmploymentType.tenant_id == tenant_id)
        .order_by(EmploymentType.name)  # type: ignore[arg-type]
    ).all()
    return [EmploymentTypeResponse.model_validate(et) for et in employment_types]


def get_employment_type(
    session: Session, tenant_id: str, employment_type_id: uuid.UUID
) -> EmploymentTypeResponse:
    """指定したEmploymentTypeを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 取得対象のEmploymentTypeID。

    Returns:
        EmploymentTypeレスポンスモデル。

    Raises:
        HTTPException: EmploymentTypeが存在しない、または異なるテナントに属する場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )
    return EmploymentTypeResponse.model_validate(employment_type)


def update_employment_type(
    session: Session,
    tenant_id: str,
    employment_type_id: uuid.UUID,
    data: EmploymentTypeUpdate,
) -> EmploymentTypeResponse:
    """指定したEmploymentTypeを更新する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 更新対象のEmploymentTypeID。
        data: EmploymentType更新リクエストデータ。

    Returns:
        更新後のEmploymentTypeレスポンスモデル。

    Raises:
        HTTPException: EmploymentTypeが存在しない場合、または更新後の名前が重複する場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )

    if data.name is not None and data.name != employment_type.name:
        existing = session.exec(
            select(EmploymentType).where(
                EmploymentType.tenant_id == tenant_id,
                EmploymentType.name == data.name,
                EmploymentType.id != employment_type_id,  # type: ignore[arg-type]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"EmploymentType '{data.name}' already exists.",
            )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employment_type, field, value)

    session.add(employment_type)
    session.commit()
    session.refresh(employment_type)
    return EmploymentTypeResponse.model_validate(employment_type)


def delete_employment_type(
    session: Session, tenant_id: str, employment_type_id: uuid.UUID
) -> None:
    """指定したEmploymentTypeを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 削除対象のEmploymentTypeID。

    Raises:
        HTTPException: EmploymentTypeが存在しない場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )
    session.delete(employment_type)
    session.commit()
