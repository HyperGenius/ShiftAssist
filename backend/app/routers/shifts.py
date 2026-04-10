# backend/app/routers/shifts.py
"""シフト関連ルーター.

ベースパス: ``/api/shifts``
シフト作成画面で使用するバリデーションコンテキストの一括取得エンドポイントを提供する。
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import ValidationContextResponse
from app.services import validation_context_service

router = APIRouter(prefix="/api/shifts", tags=["shifts"])


@router.get("/validation-context", response_model=ValidationContextResponse)
def get_validation_context(
    target_year_month: str = Query(
        ...,
        description="対象年月（YYYY-MM形式）。例: '2026-04'",
        pattern=r"^\d{4}-\d{2}$",
    ),
    start_date: date | None = Query(
        None,
        description=(
            "直近シフト日付の検索開始日（YYYY-MM-DD形式）。"
            "月跨ぎの勤務間隔チェックのため (月初日 - min_interval_days) を指定する。"
            "省略時は全期間が対象になる。"
        ),
    ),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ValidationContextResponse:
    """シフト作成画面マウント時の一括バリデーションコンテキストを返す.

    シフト編集画面で必要な全データ（ワーカー情報・実績サマリー）を
    一括で返すことで、フロントエンドのリアルタイムバリデーションを
    パフォーマンス効率よく実現する。

    ``start_date`` を指定すると、その日付以降の確定済み（published）
    ShiftPlan のアサインも直近シフト日付の計算に含まれる。
    月跨ぎの ``min_interval_days`` 検証に利用する。

    Args:
        target_year_month: 対象年月（YYYY-MM形式）。
        start_date: 直近シフト日付の検索開始日（省略可）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        バリデーションコンテキスト（ワーカー一覧 + 実績サマリー）。
    """
    return validation_context_service.get_validation_context(
        session, tenant_id, target_year_month, start_date
    )
