# backend/app/routers/worker_stats.py
"""ワーカー勤務実績統計APIルーター.

ベースパス: ``/api/workers`` および ``/api/tenants``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    AggregateStatsResponse,
    TenantStatsConfigResponse,
    TenantStatsConfigUpdate,
    TenantWorkerStatsResponse,
    WorkerStatsResponse,
)
from app.services import worker_stats_service

router = APIRouter(tags=["worker-stats"])


@router.get(
    "/api/tenants/{tenant_id}/worker-stats",
    response_model=TenantWorkerStatsResponse,
)
def get_tenant_worker_stats(
    tenant_id: str,
    x_tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> TenantWorkerStatsResponse:
    """テナント内の全ワーカーの勤務実績統計を一括取得する.

    ``published`` ステータスのシフトプランのみを集計対象とする。

    Args:
        tenant_id: パスパラメーターのテナントID。
        x_tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID（認証用）。
        session: DBセッション。

    Returns:
        テナント全ワーカーの統計一括レスポンス。
    """
    return worker_stats_service.get_all_worker_stats(session, tenant_id)


@router.get(
    "/api/workers/{worker_id}/stats",
    response_model=WorkerStatsResponse,
)
def get_worker_stats(
    worker_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerStatsResponse:
    """指定ワーカーの勤務実績統計を取得する.

    ``published`` ステータスのシフトプランのみを集計対象とする。
    在籍期間を考慮した月平均値を算出する。

    Args:
        worker_id: 集計対象のワーカーID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        ワーカーの統計レスポンス。
    """
    return worker_stats_service.get_worker_stats(session, tenant_id, worker_id)


@router.get(
    "/api/tenants/{tenant_id}/stats-config",
    response_model=TenantStatsConfigResponse,
)
def get_stats_config(
    tenant_id: str,
    x_tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> TenantStatsConfigResponse:
    """テナントの統計設定を取得する.

    Args:
        tenant_id: パスパラメーターのテナントID。
        x_tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID（認証用）。
        session: DBセッション。

    Returns:
        テナント統計設定レスポンス。
    """
    return worker_stats_service.get_stats_config(session, tenant_id)


@router.put(
    "/api/tenants/{tenant_id}/stats-config",
    response_model=TenantStatsConfigResponse,
)
def update_stats_config(
    tenant_id: str,
    data: TenantStatsConfigUpdate,
    x_tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> TenantStatsConfigResponse:
    """テナントの統計設定を更新する.

    Args:
        tenant_id: パスパラメーターのテナントID。
        data: 更新する統計設定。
        x_tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID（認証用）。
        session: DBセッション。

    Returns:
        更新後のテナント統計設定レスポンス。
    """
    return worker_stats_service.update_stats_config(
        session, tenant_id, data.stats_period_months
    )


@router.get(
    "/api/tenants/{tenant_id}/worker-stats/aggregate",
    response_model=AggregateStatsResponse,
)
def get_aggregate_stats(
    tenant_id: str,
    year_month: str | None = Query(
        default=None,
        description="集計末月（YYYY-MM形式）。省略時は当月。",
        pattern=r"^\d{4}-\d{2}$",
    ),
    x_tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> AggregateStatsResponse:
    """選択年月を末月とした直近12ヶ月のSlotType別集計を全ワーカーについて返す.

    ``published`` ステータスのシフトプランのみを集計対象とする。
    ``Worker.joined_at`` による有効月数正規化を適用した月平均を返す。
    ``weekday_night`` は月〜木の曜日別集計を含む。

    Args:
        tenant_id: パスパラメーターのテナントID。
        year_month: 集計末月（YYYY-MM形式）。省略時は当月。
        x_tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID（認証用）。
        session: DBセッション。

    Returns:
        AggregateStatsResponse。
    """
    if year_month is None:
        today = datetime.now(UTC).date()
        year_month = f"{today.year:04d}-{today.month:02d}"
    return worker_stats_service.get_aggregate_stats(session, tenant_id, year_month)
