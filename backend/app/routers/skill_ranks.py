# backend/app/routers/skill_ranks.py
"""TenantSkillRank CRUDルーター.

ベースパス: ``/api/skill-ranks``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    TenantSkillRankCreate,
    TenantSkillRankResponse,
    TenantSkillRankUpdate,
)
from app.services import skill_rank_service

router = APIRouter(prefix="/api/skill-ranks", tags=["skill-ranks"])


@router.get("/", response_model=list[TenantSkillRankResponse])
def list_skill_ranks(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[TenantSkillRankResponse]:
    """テナントに属するスキルランク一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        スキルランク一覧（sort_order昇順）。
    """
    return skill_rank_service.list_skill_ranks(session, tenant_id)


@router.post("/", response_model=TenantSkillRankResponse, status_code=status.HTTP_201_CREATED)
def create_skill_rank(
    data: TenantSkillRankCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> TenantSkillRankResponse:
    """新しいスキルランクを作成する.

    Args:
        data: スキルランク作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたスキルランクの情報。
    """
    return skill_rank_service.create_skill_rank(session, tenant_id, data)


@router.get("/{skill_rank_id}", response_model=TenantSkillRankResponse)
def get_skill_rank(
    skill_rank_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> TenantSkillRankResponse:
    """指定したスキルランクを取得する.

    Args:
        skill_rank_id: 取得対象のスキルランクID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        スキルランクの情報。
    """
    return skill_rank_service.get_skill_rank(session, tenant_id, skill_rank_id)


@router.put("/{skill_rank_id}", response_model=TenantSkillRankResponse)
def update_skill_rank(
    skill_rank_id: uuid.UUID,
    data: TenantSkillRankUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> TenantSkillRankResponse:
    """指定したスキルランクを更新する.

    Args:
        skill_rank_id: 更新対象のスキルランクID。
        data: スキルランク更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のスキルランクの情報。
    """
    return skill_rank_service.update_skill_rank(session, tenant_id, skill_rank_id, data)


@router.delete("/{skill_rank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill_rank(
    skill_rank_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したスキルランクを物理削除する.

    Args:
        skill_rank_id: 削除対象のスキルランクID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    skill_rank_service.delete_skill_rank(session, tenant_id, skill_rank_id)
