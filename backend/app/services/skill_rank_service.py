# backend/app/services/skill_rank_service.py
"""TenantSkillRank CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import TenantSkillRank
from app.models.schemas import (
    TenantSkillRankCreate,
    TenantSkillRankResponse,
    TenantSkillRankUpdate,
)


def create_skill_rank(
    session: Session, tenant_id: str, data: TenantSkillRankCreate
) -> TenantSkillRankResponse:
    """新しいTenantSkillRankを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: TenantSkillRank作成リクエストデータ。

    Returns:
        作成されたTenantSkillRankのレスポンスモデル。
    """
    rank = TenantSkillRank(
        tenant_id=tenant_id,
        name=data.name,
        sort_order=data.sort_order,
        is_leader_eligible=data.is_leader_eligible,
    )
    session.add(rank)
    session.commit()
    session.refresh(rank)
    return TenantSkillRankResponse.model_validate(rank)


def list_skill_ranks(session: Session, tenant_id: str) -> list[TenantSkillRankResponse]:
    """テナントに属するTenantSkillRank一覧を取得する（sort_order昇順）.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        TenantSkillRank一覧のレスポンスモデルリスト。
    """
    ranks = session.exec(
        select(TenantSkillRank)
        .where(TenantSkillRank.tenant_id == tenant_id)
        .order_by(TenantSkillRank.sort_order)  # type: ignore[arg-type]
    ).all()
    return [TenantSkillRankResponse.model_validate(r) for r in ranks]


def get_skill_rank(
    session: Session, tenant_id: str, skill_rank_id: uuid.UUID
) -> TenantSkillRankResponse:
    """指定したTenantSkillRankを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        skill_rank_id: 取得対象のスキルランクID。

    Returns:
        TenantSkillRankレスポンスモデル。

    Raises:
        HTTPException: スキルランクが存在しない、または異なるテナントに属する場合。
    """
    rank = session.exec(
        select(TenantSkillRank).where(
            TenantSkillRank.id == skill_rank_id,  # type: ignore[arg-type]
            TenantSkillRank.tenant_id == tenant_id,
        )
    ).first()
    if rank is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SkillRank '{skill_rank_id}' not found.",
        )
    return TenantSkillRankResponse.model_validate(rank)


def update_skill_rank(
    session: Session,
    tenant_id: str,
    skill_rank_id: uuid.UUID,
    data: TenantSkillRankUpdate,
) -> TenantSkillRankResponse:
    """指定したTenantSkillRankを更新する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        skill_rank_id: 更新対象のスキルランクID。
        data: TenantSkillRank更新リクエストデータ。

    Returns:
        更新後のTenantSkillRankレスポンスモデル。

    Raises:
        HTTPException: スキルランクが存在しない場合。
    """
    rank = session.exec(
        select(TenantSkillRank).where(
            TenantSkillRank.id == skill_rank_id,  # type: ignore[arg-type]
            TenantSkillRank.tenant_id == tenant_id,
        )
    ).first()
    if rank is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SkillRank '{skill_rank_id}' not found.",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rank, field, value)

    session.add(rank)
    session.commit()
    session.refresh(rank)
    return TenantSkillRankResponse.model_validate(rank)


def delete_skill_rank(
    session: Session, tenant_id: str, skill_rank_id: uuid.UUID
) -> None:
    """指定したTenantSkillRankを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        skill_rank_id: 削除対象のスキルランクID。

    Raises:
        HTTPException: スキルランクが存在しない場合。
    """
    rank = session.exec(
        select(TenantSkillRank).where(
            TenantSkillRank.id == skill_rank_id,  # type: ignore[arg-type]
            TenantSkillRank.tenant_id == tenant_id,
        )
    ).first()
    if rank is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SkillRank '{skill_rank_id}' not found.",
        )
    session.delete(rank)
    session.commit()
