# backend/app/routers/departments.py
"""Department CRUDルーター.

ベースパス: ``/api/departments``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    DepartmentBulkPreviewResponse,
    DepartmentBulkRequest,
    DepartmentBulkUpsertResponse,
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services import department_service

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.post(
    "/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED
)
def create_department(
    data: DepartmentCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> DepartmentResponse:
    """新しいDepartmentを作成する.

    Args:
        data: Department作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたDepartmentの情報。
    """
    return department_service.create_department(session, tenant_id, data)


@router.get("/", response_model=DepartmentListResponse)
def list_departments(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
    skip: int = Query(default=0, ge=0, description="スキップ件数"),
    limit: int = Query(default=100, ge=1, le=1000, description="取得上限件数"),
    search: str | None = Query(default=None, description="部門名の部分一致検索クエリ"),
) -> DepartmentListResponse:
    """テナントに属するDepartment一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
        skip: スキップ件数（ページネーション用）。
        limit: 取得上限件数（ページネーション用）。
        search: 部門名の部分一致検索クエリ。

    Returns:
        合計件数と部門一覧。
    """
    return department_service.list_departments(
        session, tenant_id, skip=skip, limit=limit, search_query=search
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> DepartmentResponse:
    """指定したDepartmentを取得する.

    Args:
        department_id: 取得対象のDepartment ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Departmentの情報。
    """
    return department_service.get_department(session, tenant_id, department_id)


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: uuid.UUID,
    data: DepartmentUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> DepartmentResponse:
    """指定したDepartmentを更新する.

    Args:
        department_id: 更新対象のDepartment ID。
        data: Department更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のDepartmentの情報。
    """
    return department_service.update_department(session, tenant_id, department_id, data)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したDepartmentを論理削除する.

    所属するWorkerが存在する場合は HTTP 409 を返す。

    Args:
        department_id: 削除対象のDepartment ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    department_service.delete_department(session, tenant_id, department_id)


@router.post(
    "/bulk/preview",
    response_model=DepartmentBulkPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_bulk_upsert_departments(
    data: DepartmentBulkRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> DepartmentBulkPreviewResponse:
    """Department一括登録・更新のプレビューを取得する.

    実際のDB更新は行わず、「新規追加」「名称変更」「再活性化」の件数とリストを返す。

    Args:
        data: バルク処理リクエストボディ（Departmentリスト）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        プレビュー情報（件数・差分リスト）。
    """
    return department_service.preview_bulk_upsert_departments(
        session, tenant_id, data.departments
    )


@router.post(
    "/bulk",
    response_model=DepartmentBulkUpsertResponse,
    status_code=status.HTTP_200_OK,
)
def bulk_upsert_departments(
    data: DepartmentBulkRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> DepartmentBulkUpsertResponse:
    """Departmentを一括登録・更新する（Upsert）.

    - 同じ ``code`` の有効・論理削除済みレコードがある場合: ``name`` を更新し再活性化。
    - 一致する ``code`` がない場合: 新規作成。
    - リスト内に重複する ``code`` がある場合は HTTP 422 を返す。

    Args:
        data: バルク処理リクエストボディ（Departmentリスト）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成・更新・再活性化の件数と処理後のDepartmentリスト。
    """
    return department_service.bulk_upsert_departments(
        session, tenant_id, data.departments
    )
