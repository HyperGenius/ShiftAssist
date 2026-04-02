# backend/app/routers/rules.py
"""シフトルール定義APIルーター.

ベースパス: ``/api/rules``
フロントエンドがシフト作成ルールを取得・更新するためのエンドポイントを提供する。
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.rule_schemas import ShiftRulesResponse
from app.services import shift_rules_service

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/", response_model=ShiftRulesResponse)
def get_rules(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftRulesResponse:
    """現在のシフトルール定義を取得する.

    テナント固有のルールがDBに存在する場合はそれを返し、
    存在しない場合はデフォルト値を返す。

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        シフトルール定義（shift_rules と warnings を含む）。
    """
    return shift_rules_service.get_shift_rules(session, tenant_id)


@router.put("/", response_model=ShiftRulesResponse)
def update_rules(
    data: ShiftRulesResponse,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftRulesResponse:
    """シフトルール定義を更新する.

    テナント管理者がUIから変更したルール設定を受け取り、DBに保存する。
    レコードが存在しない場合は新規作成し、存在する場合は上書き更新する。

    Args:
        data: 更新するシフトルール定義。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のシフトルール定義。
    """
    return shift_rules_service.update_shift_rules(session, tenant_id, data)
