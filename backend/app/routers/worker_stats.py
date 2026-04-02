# backend/app/routers/worker_stats.py
"""ワーカー勤務実績統計APIルーター.

ベースパス: ``/api/workers`` および ``/api/tenants``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
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
