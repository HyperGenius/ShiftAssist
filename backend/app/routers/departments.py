# backend/app/routers/departments.py
"""Department CRUDルーター.

ベースパス: ``/api/departments``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services import department_service

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[DepartmentResponse]:
    """テナントに属するDepartment一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Department一覧。
    """
    return department_service.list_departments(session, tenant_id)


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
    """指定したDepartmentを物理削除する.

    所属するWorkerが存在する場合は HTTP 409 を返す。

    Args:
        department_id: 削除対象のDepartment ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    department_service.delete_department(session, tenant_id, department_id)
