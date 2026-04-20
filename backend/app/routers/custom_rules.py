# backend/app/routers/custom_rules.py
"""カスタムルール CRUDルーター.

ベースパス: ``/api/custom-rules``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import CustomRuleCreate, CustomRuleResponse, CustomRuleUpdate
from app.services import custom_rule_service

router = APIRouter(prefix="/api/custom-rules", tags=["custom-rules"])


@router.get("/", response_model=list[CustomRuleResponse])
def list_custom_rules(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[CustomRuleResponse]:
    """テナントに属するカスタムルール一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        カスタムルール一覧（名前昇順）。
    """
    return custom_rule_service.list_custom_rules(session, tenant_id)


@router.post(
    "/", response_model=CustomRuleResponse, status_code=status.HTTP_201_CREATED
)
def create_custom_rule(
    data: CustomRuleCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> CustomRuleResponse:
    """新しいカスタムルールを作成する.

    Args:
        data: カスタムルール作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたカスタムルールの情報。
    """
    return custom_rule_service.create_custom_rule(session, tenant_id, data)


@router.get("/{rule_id}", response_model=CustomRuleResponse)
def get_custom_rule(
    rule_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> CustomRuleResponse:
    """指定したカスタムルールを取得する.

    Args:
        rule_id: 取得対象のカスタムルール ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        カスタムルールの情報。
    """
    return custom_rule_service.get_custom_rule(session, tenant_id, rule_id)


@router.put("/{rule_id}", response_model=CustomRuleResponse)
def update_custom_rule(
    rule_id: uuid.UUID,
    data: CustomRuleUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> CustomRuleResponse:
    """指定したカスタムルールを更新する.

    Args:
        rule_id: 更新対象のカスタムルール ID。
        data: カスタムルール更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のカスタムルールの情報。
    """
    return custom_rule_service.update_custom_rule(session, tenant_id, rule_id, data)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_rule(
    rule_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したカスタムルールを物理削除する.

    削除されると、このルールをアサインされているWorkerの ``custom_rule_id`` は
    自動的に NULL にリセットされる（CASCADE SET NULL）。

    Args:
        rule_id: 削除対象のカスタムルール ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    custom_rule_service.delete_custom_rule(session, tenant_id, rule_id)
