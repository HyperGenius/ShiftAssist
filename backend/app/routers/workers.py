# backend/app/routers/workers.py
"""Worker CRUDルーター.

ベースパス: ``/api/workers``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    WorkerBulkPreviewResponse,
    WorkerBulkRequest,
    WorkerBulkUpsertResponse,
    WorkerCreate,
    WorkerResponse,
    WorkerUpdate,
    WorkerUploadPreviewResponse,
    WorkerUploadUpsertResponse,
)
from app.services import worker_service, worker_upload_service

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.post(
    "/bulk/preview",
    response_model=WorkerBulkPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_bulk_workers(
    data: WorkerBulkRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerBulkPreviewResponse:
    """Worker一括登録・更新の差分プレビューを返す.

    実際のDB更新は行わず、「新規追加」「更新」「変更なし」の件数と
    未登録の課の自動生成件数を返す。

    Args:
        data: Worker一括処理リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        差分プレビューレスポンス。
    """
    return worker_service.preview_bulk_upsert_workers(session, tenant_id, data.workers)


@router.post(
    "/bulk",
    response_model=WorkerBulkUpsertResponse,
    status_code=status.HTTP_200_OK,
)
def bulk_upsert_workers(
    data: WorkerBulkRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerBulkUpsertResponse:
    """Workerを一括登録・更新する（Upsert）.

    未登録の課（Department）が含まれる場合、自動的に新規登録する。

    Args:
        data: Worker一括処理リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成・更新件数と処理後のWorkerリスト。
    """
    return worker_service.bulk_upsert_workers(session, tenant_id, data.workers)


@router.post(
    "/upload",
    status_code=status.HTTP_200_OK,
)
async def upload_workers(
    file: UploadFile,
    dry_run: bool = Query(
        True,
        description="Trueの場合はDry-run（プレビューのみ）、Falseの場合はUpsert実行",
    ),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> WorkerUploadPreviewResponse | WorkerUploadUpsertResponse:
    """CSV/ExcelファイルからWorkerを一括登録・更新する.

    ``dry_run=true``（デフォルト）の場合はDB更新を行わず、差分プレビューを返す。
    ``dry_run=false``の場合はバリデーション後にUpsertを実行する。

    対応ファイル形式:
    - CSV（UTF-8、UTF-8 BOM付き、Shift-JIS）
    - Excel（.xlsx）

    必須列: 職員番号, 氏名
    任意列: 生年月日, 現在のスキル取得日, 役職名, 支所名, 課名,
            異動種別, 異動予定月, 事業本部変更の有無, スキルランク名

    Args:
        file: アップロードするCSV/Excelファイル。
        dry_run: Trueの場合はDry-runのみ（デフォルト: True）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        dry_run=TrueのときはWorkerUploadPreviewResponse、
        dry_run=FalseのときはWorkerUploadUpsertResponse。
    """
    filename = file.filename or ""
    content = await file.read()

    if filename.endswith(".xlsx") or file.content_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        raw_rows = worker_upload_service.parse_excel_bytes(content)
    elif filename.endswith(".csv") or file.content_type in (
        "text/csv",
        "text/plain",
        "application/csv",
    ):
        raw_rows = worker_upload_service.parse_csv_bytes(content)
    else:
        # content_typeが不明な場合はCSVとして試みる
        try:
            raw_rows = worker_upload_service.parse_csv_bytes(content)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="対応しているファイル形式はCSV（.csv）またはExcel（.xlsx）のみです。",
            ) from None

    if dry_run:
        return worker_upload_service.preview_upload(session, tenant_id, raw_rows)
    else:
        return worker_upload_service.execute_upload(session, tenant_id, raw_rows)


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
