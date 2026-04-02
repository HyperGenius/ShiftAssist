# backend/app/services/department_service.py
"""Department CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.models import Department, Worker
from app.models.schemas import (
    DepartmentBulkItem,
    DepartmentBulkPreviewItem,
    DepartmentBulkPreviewResponse,
    DepartmentBulkUpsertResponse,
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
    """テナントに属するDepartment一覧を取得する（論理削除済みを除く）.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        skip: スキップ件数（ページネーション用）。
        limit: 取得上限件数（ページネーション用）。
        search_query: 部門名の部分一致検索クエリ。

    Returns:
        合計件数と部門一覧を含むレスポンスモデル。
    """
    stmt = select(Department).where(
        Department.tenant_id == tenant_id,
        Department.deleted_at.is_(None),  # type: ignore[attr-defined]
    )
    count_stmt = select(func.count(Department.id)).where(  # type: ignore[arg-type]
        Department.tenant_id == tenant_id,
        Department.deleted_at.is_(None),  # type: ignore[attr-defined]
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
    """指定したDepartmentを取得する（論理削除済みを除く）.

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
            Department.deleted_at.is_(None),  # type: ignore[attr-defined]
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
            Department.deleted_at.is_(None),  # type: ignore[attr-defined]
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
    """指定したDepartmentを論理削除する.

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
            Department.deleted_at.is_(None),  # type: ignore[attr-defined]
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

    department.deleted_at = datetime.now(tz=UTC)
    session.add(department)
    session.commit()


def preview_bulk_upsert_departments(
    session: Session,
    tenant_id: str,
    items: list[DepartmentBulkItem],
) -> DepartmentBulkPreviewResponse:
    """一括登録・更新の差分プレビューを返す.

    実際のDB更新は行わず、「新規追加」「名称変更」「再活性化」の件数とリストを返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        items: 登録・更新対象のDepartmentアイテムリスト。

    Returns:
        プレビューレスポンス（件数・差分リスト）。

    Raises:
        HTTPException: 重複するcodeが存在する場合（HTTP 422）。
    """
    _validate_no_duplicate_codes(items)

    codes = [item.code for item in items]
    existing_map = _fetch_existing_by_codes(session, tenant_id, codes)

    preview_items: list[DepartmentBulkPreviewItem] = []
    create_count = update_count = reactivate_count = no_change_count = 0

    for item in items:
        existing = existing_map.get(item.code)
        if existing is None:
            preview_items.append(
                DepartmentBulkPreviewItem(code=item.code, name=item.name, action="create")
            )
            create_count += 1
        elif existing.deleted_at is not None:
            preview_items.append(
                DepartmentBulkPreviewItem(
                    code=item.code,
                    name=item.name,
                    action="reactivate",
                    old_name=existing.name,
                )
            )
            reactivate_count += 1
        elif existing.name != item.name:
            preview_items.append(
                DepartmentBulkPreviewItem(
                    code=item.code,
                    name=item.name,
                    action="update",
                    old_name=existing.name,
                )
            )
            update_count += 1
        else:
            # 変更なし
            preview_items.append(
                DepartmentBulkPreviewItem(code=item.code, name=item.name, action="no_change")
            )
            no_change_count += 1

    return DepartmentBulkPreviewResponse(
        preview=preview_items,
        create_count=create_count,
        update_count=update_count,
        reactivate_count=reactivate_count,
        no_change_count=no_change_count,
    )


def bulk_upsert_departments(
    session: Session,
    tenant_id: str,
    items: list[DepartmentBulkItem],
) -> DepartmentBulkUpsertResponse:
    """Departmentを一括登録・更新する（Upsert）.

    - 同じ ``code`` の有効・論理削除済みレコードがある場合: ``name`` を更新し ``deleted_at`` をNULLに戻す（再活性化）。
    - 一致する ``code`` がない場合: 新規作成。
    アトミックな処理として、エラー時はすべてロールバックされる。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        items: 登録・更新対象のDepartmentアイテムリスト。

    Returns:
        作成・更新・再活性化の件数と処理後のDepartmentリスト。

    Raises:
        HTTPException: 重複するcodeが存在する場合（HTTP 422）。
    """
    _validate_no_duplicate_codes(items)

    codes = [item.code for item in items]
    existing_map = _fetch_existing_by_codes(session, tenant_id, codes)

    created = updated = reactivated = 0
    result_items: list[Department] = []

    for item in items:
        existing = existing_map.get(item.code)
        if existing is None:
            dept = Department(
                tenant_id=tenant_id,
                name=item.name,
                code=item.code,
            )
            session.add(dept)
            created += 1
            result_items.append(dept)
        else:
            if existing.deleted_at is not None:
                reactivated += 1
            elif existing.name != item.name:
                updated += 1
            # else: 変更なし（カウントしない）
            existing.name = item.name
            existing.deleted_at = None
            session.add(existing)
            result_items.append(existing)

    session.commit()
    for dept in result_items:
        session.refresh(dept)

    return DepartmentBulkUpsertResponse(
        created=created,
        updated=updated,
        reactivated=reactivated,
        items=[DepartmentResponse.model_validate(d) for d in result_items],
    )


def _validate_no_duplicate_codes(items: list[DepartmentBulkItem]) -> None:
    """リスト内の重複codeをチェックし、重複がある場合は例外を送出する."""
    codes = [item.code for item in items]
    if len(codes) != len(set(codes)):
        seen: set[str] = set()
        duplicates: list[str] = []
        for code in codes:
            if code in seen:
                duplicates.append(code)
            seen.add(code)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"重複するcodeが含まれています: {', '.join(duplicates)}",
        )


def _fetch_existing_by_codes(
    session: Session,
    tenant_id: str,
    codes: list[str],
) -> dict[str, Department]:
    """指定したコード一覧に対応するDepartmentを（論理削除済み含む）取得してdict化する."""
    if not codes:
        return {}
    rows = session.exec(
        select(Department).where(
            Department.tenant_id == tenant_id,
            Department.code.in_(codes),  # type: ignore[attr-defined]
        )
    ).all()
    return {row.code: row for row in rows}

