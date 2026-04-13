# backend/app/routers/employment_types.py
"""EmploymentType CRUDルーター.

ベースパス: ``/api/employment-types``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.rule_schemas import EmploymentTypeRuleConfig
from app.models.schemas import (
    EmploymentTypeCreate,
    EmploymentTypeResponse,
    EmploymentTypeRuleUpdate,
    EmploymentTypeUpdate,
)
from app.services import employment_type_service

router = APIRouter(prefix="/api/employment-types", tags=["employment-types"])


@router.get("/", response_model=list[EmploymentTypeResponse])
def list_employment_types(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[EmploymentTypeResponse]:
    """テナントに属する雇用形態一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        雇用形態一覧（名前昇順）。
    """
    return employment_type_service.list_employment_types(session, tenant_id)


@router.post(
    "/", response_model=EmploymentTypeResponse, status_code=status.HTTP_201_CREATED
)
def create_employment_type(
    data: EmploymentTypeCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> EmploymentTypeResponse:
    """新しい雇用形態を作成する.

    Args:
        data: 雇用形態作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成された雇用形態の情報。
    """
    return employment_type_service.create_employment_type(session, tenant_id, data)


@router.get("/{employment_type_id}", response_model=EmploymentTypeResponse)
def get_employment_type(
    employment_type_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> EmploymentTypeResponse:
    """指定した雇用形態を取得する.

    Args:
        employment_type_id: 取得対象の雇用形態ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        雇用形態の情報。
    """
    return employment_type_service.get_employment_type(
        session, tenant_id, employment_type_id
    )


@router.put("/{employment_type_id}", response_model=EmploymentTypeResponse)
def update_employment_type(
    employment_type_id: uuid.UUID,
    data: EmploymentTypeUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> EmploymentTypeResponse:
    """指定した雇用形態を更新する.

    Args:
        employment_type_id: 更新対象の雇用形態ID。
        data: 雇用形態更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後の雇用形態の情報。
    """
    return employment_type_service.update_employment_type(
        session, tenant_id, employment_type_id, data
    )


@router.delete("/{employment_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employment_type(
    employment_type_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定した雇用形態を物理削除する.

    Args:
        employment_type_id: 削除対象の雇用形態ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    employment_type_service.delete_employment_type(
        session, tenant_id, employment_type_id
    )


@router.get("/{employment_type_id}/rules", response_model=EmploymentTypeRuleConfig)
def get_employment_type_rules(
    employment_type_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> EmploymentTypeRuleConfig:
    """指定した雇用形態のルール設定を取得する.

    Args:
        employment_type_id: 取得対象の雇用形態ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        雇用形態別ルール設定（未設定の場合はデフォルト値）。
    """
    return employment_type_service.get_employment_type_rule(
        session, tenant_id, employment_type_id
    )


@router.put("/{employment_type_id}/rules", response_model=EmploymentTypeRuleConfig)
def update_employment_type_rules(
    employment_type_id: uuid.UUID,
    data: EmploymentTypeRuleUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> EmploymentTypeRuleConfig:
    """指定した雇用形態のルール設定を更新（upsert）する.

    Args:
        employment_type_id: 更新対象の雇用形態ID。
        data: ルール設定の更新データ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後の雇用形態別ルール設定。
    """
    return employment_type_service.upsert_employment_type_rule(
        session, tenant_id, employment_type_id, data
    )
