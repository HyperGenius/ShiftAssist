# backend/app/routers/workers.py
"""Worker CRUDルーター.

ベースパス: ``/api/workers``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import WorkerCreate, WorkerResponse, WorkerUpdate
from app.services import worker_service

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.post("/", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def create_worker(
    data: WorkerCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerResponse:
    """新しいWorkerを作成する.

    Args:
        data: Worker作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたWorkerの情報。
    """
    return worker_service.create_worker(session, tenant_id, data)


@router.get("/", response_model=list[WorkerResponse])
def list_workers(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[WorkerResponse]:
    """テナントに属するWorker一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Worker一覧。
    """
    return worker_service.list_workers(session, tenant_id)


@router.get("/{worker_id}", response_model=WorkerResponse)
def get_worker(
    worker_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerResponse:
    """指定したWorkerを取得する.

    Args:
        worker_id: 取得対象のWorker ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Workerの情報。
    """
    return worker_service.get_worker(session, tenant_id, worker_id)


@router.put("/{worker_id}", response_model=WorkerResponse)
def update_worker(
    worker_id: uuid.UUID,
    data: WorkerUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerResponse:
    """指定したWorkerを更新する.

    Args:
        worker_id: 更新対象のWorker ID。
        data: Worker更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のWorkerの情報。
    """
    return worker_service.update_worker(session, tenant_id, worker_id, data)


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worker(
    worker_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したWorkerを物理削除する.

    Args:
        worker_id: 削除対象のWorker ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    worker_service.delete_worker(session, tenant_id, worker_id)
