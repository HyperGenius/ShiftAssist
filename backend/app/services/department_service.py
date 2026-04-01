# backend/app/services/department_service.py
"""Department CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.models import Department, Worker
from app.models.schemas import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)


def create_department(
    session: Session, tenant_id: str, data: DepartmentCreate
) -> DepartmentResponse:
    """新しいDepartmentを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: Department作成リクエストデータ。

    Returns:
        作成されたDepartmentのレスポンスモデル。
    """
    department = Department(
        tenant_id=tenant_id,
        name=data.name,
        code=data.code,
    )
    session.add(department)
    session.commit()
    session.refresh(department)
    return DepartmentResponse.model_validate(department)


def list_departments(
    session: Session,
    tenant_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
    search_query: str | None = None,
) -> DepartmentListResponse:
    """テナントに属するDepartment一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        skip: スキップ件数（ページネーション用）。
        limit: 取得上限件数（ページネーション用）。
        search_query: 部門名の部分一致検索クエリ。

    Returns:
        合計件数と部門一覧を含むレスポンスモデル。
    """
    stmt = select(Department).where(Department.tenant_id == tenant_id)
    count_stmt = select(func.count(Department.id)).where(  # type: ignore[arg-type]
        Department.tenant_id == tenant_id
    )
    if search_query:
        escaped = (
            search_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        ilike_filter = col(Department.name).ilike(f"%{escaped}%", escape="\\")
        stmt = stmt.where(ilike_filter)
        count_stmt = count_stmt.where(ilike_filter)

    total: int = session.exec(count_stmt).one()  # type: ignore[assignment]
    departments = session.exec(stmt.offset(skip).limit(limit)).all()
    return DepartmentListResponse(
        total=total,
        items=[DepartmentResponse.model_validate(d) for d in departments],
    )


def get_department(
    session: Session, tenant_id: str, department_id: uuid.UUID
) -> DepartmentResponse:
    """指定したDepartmentを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        department_id: 取得対象のDepartment ID。

    Returns:
        Departmentレスポンスモデル。

    Raises:
        HTTPException: Departmentが存在しない、または異なるテナントに属する場合。
    """
    department = session.exec(
        select(Department).where(
            Department.id == department_id,  # type: ignore[arg-type]
            Department.tenant_id == tenant_id,
        )
    ).first()
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{department_id}' not found.",
        )
    return DepartmentResponse.model_validate(department)


def update_department(
    session: Session,
    tenant_id: str,
    department_id: uuid.UUID,
    data: DepartmentUpdate,
) -> DepartmentResponse:
    """指定したDepartmentを更新する.

    ``model_dump(exclude_unset=True)`` により、指定されたフィールドのみを更新する。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        department_id: 更新対象のDepartment ID。
        data: Department更新リクエストデータ。

    Returns:
        更新後のDepartmentレスポンスモデル。

    Raises:
        HTTPException: Departmentが存在しない場合。
    """
    department = session.exec(
        select(Department).where(
            Department.id == department_id,  # type: ignore[arg-type]
            Department.tenant_id == tenant_id,
        )
    ).first()
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{department_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    session.add(department)
    session.commit()
    session.refresh(department)
    return DepartmentResponse.model_validate(department)


def delete_department(
    session: Session, tenant_id: str, department_id: uuid.UUID
) -> None:
    """指定したDepartmentを物理削除する.

    所属するWorkerが存在する場合は削除をブロックし、HTTP 409 を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        department_id: 削除対象のDepartment ID。

    Raises:
        HTTPException: Departmentが存在しない場合、または所属するWorkerが存在する場合。
    """
    department = session.exec(
        select(Department).where(
            Department.id == department_id,  # type: ignore[arg-type]
            Department.tenant_id == tenant_id,
        )
    ).first()
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{department_id}' not found.",
        )

    worker = session.exec(
        select(Worker).where(
            Worker.department_id == department_id,  # type: ignore[arg-type]
            Worker.tenant_id == tenant_id,
        )
    ).first()
    if worker is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="所属しているスタッフがいるため削除できません。",
        )

    session.delete(department)
    session.commit()
