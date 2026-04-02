# backend/app/routers/rules.py
"""シフトルール定義APIルーター.

ベースパス: ``/api/rules``
フロントエンドがシフト作成ルールを取得するためのエンドポイントを提供する。
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_tenant_id
from app.models.rule_schemas import ShiftRulesResponse
from app.services import shift_rules_service

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/", response_model=ShiftRulesResponse)
def get_rules(
    tenant_id: str = Depends(get_tenant_id),
) -> ShiftRulesResponse:
    """現在のシフトルール定義を取得する.

    フロントエンドはこのエンドポイントからルール定義を取得し、
    リアルタイムバリデーションに使用する。

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。

    Returns:
        シフトルール定義（shift_rules と warnings を含む）。
    """
    return shift_rules_service.get_shift_rules()
