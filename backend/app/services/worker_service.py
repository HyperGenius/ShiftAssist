# backend/app/services/worker_service.py
"""Worker CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import Department, EmploymentType, TenantSkillRank, Worker
from app.models.schemas import (
    WorkerBulkItem,
    WorkerBulkPreviewItem,
    WorkerBulkPreviewResponse,
    WorkerBulkUpsertResponse,
    WorkerCreate,
    WorkerResponse,
    WorkerUpdate,
)


def _validate_department(
    session: Session, tenant_id: str, department_id: uuid.UUID
) -> None:
    """指定された ``department_id`` が同一テナントに存在するか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        department_id: 検証対象の所属課ID。

    Raises:
        HTTPException: 所属課が存在しない、または異なるテナントに属する場合。
    """
    dept = session.exec(
        select(Department).where(
            Department.id == department_id,  # type: ignore[arg-type]
            Department.tenant_id == tenant_id,
        )
    ).first()
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department '{department_id}' not found in tenant.",
        )


def _validate_skill_rank(
    session: Session, tenant_id: str, skill_rank_id: uuid.UUID
) -> None:
    """指定された ``skill_rank_id`` が同一テナントに存在するか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        skill_rank_id: 検証対象のスキルランクID。

    Raises:
        HTTPException: スキルランクが存在しない、または異なるテナントに属する場合。
    """
    rank = session.exec(
        select(TenantSkillRank).where(
            TenantSkillRank.id == skill_rank_id,  # type: ignore[arg-type]
            TenantSkillRank.tenant_id == tenant_id,
        )
    ).first()
    if rank is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SkillRank '{skill_rank_id}' not found in tenant.",
        )


def _validate_employment_type(
    session: Session, tenant_id: str, employment_type_id: uuid.UUID
) -> None:
    """指定された ``employment_type_id`` が同一テナントに存在するか検証する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        employment_type_id: 検証対象の雇用形態ID。

    Raises:
        HTTPException: 雇用形態が存在しない、または異なるテナントに属する場合。
    """
    et = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if et is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found in tenant.",
        )


def create_worker(
    session: Session, tenant_id: str, data: WorkerCreate
) -> WorkerResponse:
    """新しいWorkerを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: Worker作成リクエストデータ。

    Returns:
        作成されたWorkerのレスポンスモデル。

    Raises:
        HTTPException: ``department_id`` が同一テナントに存在しない場合。
    """
    _validate_department(session, tenant_id, data.department_id)
    _validate_skill_rank(session, tenant_id, data.skill_rank_id)
    if data.employment_type_id is not None:
        _validate_employment_type(session, tenant_id, data.employment_type_id)

    worker = Worker(
        tenant_id=tenant_id,
        employee_no=data.employee_no,
        employee_code=data.employee_code,
        name=data.name,
        department_id=data.department_id,
        skill_rank_id=data.skill_rank_id,
        position_id=data.position_id,
        employment_type_id=data.employment_type_id,
        birth_date=data.birth_date,
        skill_acquired_at=data.skill_acquired_at,
        transfer_type=data.transfer_type,
        transfer_scheduled_month=data.transfer_scheduled_month,
        is_cross_division_transfer=data.is_cross_division_transfer,
        joined_at=data.joined_at,
        transferred_at=data.transferred_at,
    )
    session.add(worker)
    session.commit()
    session.refresh(worker)
    return WorkerResponse.model_validate(worker)


def list_workers(session: Session, tenant_id: str) -> list[WorkerResponse]:
    """テナントに属するWorker一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        Worker一覧のレスポンスモデルリスト。
    """
    workers = session.exec(select(Worker).where(Worker.tenant_id == tenant_id)).all()
    return [WorkerResponse.model_validate(w) for w in workers]


def get_worker(
    session: Session, tenant_id: str, worker_id: uuid.UUID
) -> WorkerResponse:
    """指定したWorkerを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        worker_id: 取得対象のWorker ID。

    Returns:
        Workerレスポンスモデル。

    Raises:
        HTTPException: Workerが存在しない、または異なるテナントに属する場合。
    """
    worker = session.exec(
        select(Worker).where(
            Worker.id == worker_id,  # type: ignore[arg-type]
            Worker.tenant_id == tenant_id,
        )
    ).first()
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{worker_id}' not found.",
        )
    return WorkerResponse.model_validate(worker)


def update_worker(
    session: Session,
    tenant_id: str,
    worker_id: uuid.UUID,
    data: WorkerUpdate,
) -> WorkerResponse:
    """指定したWorkerを更新する.

    ``model_dump(exclude_unset=True)`` により、指定されたフィールドのみを更新する。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        worker_id: 更新対象のWorker ID。
        data: Worker更新リクエストデータ。

    Returns:
        更新後のWorkerレスポンスモデル。

    Raises:
        HTTPException: Workerが存在しない場合、または ``department_id`` が
            同一テナントに存在しない場合。
    """
    worker = session.exec(
        select(Worker).where(
            Worker.id == worker_id,  # type: ignore[arg-type]
            Worker.tenant_id == tenant_id,
        )
    ).first()
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{worker_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "department_id" in update_data:
        _validate_department(session, tenant_id, update_data["department_id"])

    if "skill_rank_id" in update_data:
        _validate_skill_rank(session, tenant_id, update_data["skill_rank_id"])

    if "employment_type_id" in update_data and update_data["employment_type_id"] is not None:
        _validate_employment_type(session, tenant_id, update_data["employment_type_id"])

    for field, value in update_data.items():
        setattr(worker, field, value)

    session.add(worker)
    session.commit()
    session.refresh(worker)
    return WorkerResponse.model_validate(worker)


def delete_worker(session: Session, tenant_id: str, worker_id: uuid.UUID) -> None:
    """指定したWorkerを物理削除する.

    ``ShiftAssignment`` への影響はDB制約（CASCADE DELETE）により処理される。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        worker_id: 削除対象のWorker ID。

    Raises:
        HTTPException: Workerが存在しない、または異なるテナントに属する場合。
    """
    worker = session.exec(
        select(Worker).where(
            Worker.id == worker_id,  # type: ignore[arg-type]
            Worker.tenant_id == tenant_id,
        )
    ).first()
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker '{worker_id}' not found.",
        )
    session.delete(worker)
    session.commit()


def _fetch_departments_by_codes(
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
    return {str(row.code): row for row in rows}


def _fetch_workers_by_employee_nos(
    session: Session,
    tenant_id: str,
    employee_nos: list[str],
) -> dict[str, Worker]:
    """指定した社員番号一覧に対応するWorkerを取得してdict化する."""
    if not employee_nos:
        return {}
    rows = session.exec(
        select(Worker).where(
            Worker.tenant_id == tenant_id,
            Worker.employee_no.in_(employee_nos),  # type: ignore[attr-defined]
        )
    ).all()
    return {str(row.employee_no): row for row in rows}


def _ensure_departments(
    session: Session,
    tenant_id: str,
    items: list[WorkerBulkItem],
) -> tuple[dict[str, uuid.UUID], int]:
    """データ中の課コードを解決し、未登録の課を自動生成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        items: バルク登録対象のWorkerアイテムリスト。

    Returns:
        課コード→UUID のマッピング辞書と、新規作成した課の件数のタプル。
    """
    codes = list({item.department_code for item in items})
    dept_map = _fetch_departments_by_codes(session, tenant_id, codes)

    created_count = 0
    dept_id_map: dict[str, uuid.UUID] = {}

    for code in codes:
        existing = dept_map.get(code)
        if existing is not None:
            if existing.deleted_at is not None:
                # 論理削除済みの課を再活性化
                existing.deleted_at = None  # type: ignore[assignment]
                session.add(existing)
            dept_id_map[code] = existing.id  # type: ignore[assignment]
        else:
            # 未登録の課を自動生成。department_name が未指定の場合はコードを名称として使用
            name = next(
                (
                    item.department_name
                    for item in items
                    if item.department_code == code and item.department_name
                ),
                code,
            )
            new_dept = Department(
                tenant_id=tenant_id,
                name=name,
                code=code,
            )
            session.add(new_dept)
            session.flush()  # IDを生成するためflush
            dept_id_map[code] = new_dept.id  # type: ignore[assignment]
            created_count += 1

    return dept_id_map, created_count


def preview_bulk_upsert_workers(
    session: Session,
    tenant_id: str,
    items: list[WorkerBulkItem],
) -> WorkerBulkPreviewResponse:
    """Worker一括登録・更新の差分プレビューを返す.

    実際のDB更新は行わず、「新規追加」「更新」「変更なし」の件数と
    リストを返す。未登録の課を自動生成する件数も含む。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        items: 登録・更新対象のWorkerアイテムリスト。

    Returns:
        プレビューレスポンス（件数・差分リスト）。

    Raises:
        HTTPException: 重複するemployee_noが存在する場合（HTTP 422）。
    """
    _validate_no_duplicate_employee_nos(items)

    # 既存Workerの取得
    employee_nos = [item.employee_no for item in items]
    existing_map = _fetch_workers_by_employee_nos(session, tenant_id, employee_nos)

    # 課コードの解決（新規作成対象を検出）
    dept_codes = list({item.department_code for item in items})
    dept_map = _fetch_departments_by_codes(session, tenant_id, dept_codes)
    new_dept_codes = {
        code
        for code in dept_codes
        if dept_map.get(code) is None or dept_map[code].deleted_at is not None
    }

    preview_items: list[WorkerBulkPreviewItem] = []
    create_count = update_count = no_change_count = 0

    for item in items:
        existing = existing_map.get(item.employee_no)
        dept_is_new = item.department_code in new_dept_codes

        if existing is None:
            preview_items.append(
                WorkerBulkPreviewItem(
                    employee_no=item.employee_no,
                    name=item.name,
                    department_code=item.department_code,
                    action="create",
                    department_is_new=dept_is_new,
                )
            )
            create_count += 1
        else:
            existing_dept = dept_map.get(item.department_code)
            dept_id_changed = dept_is_new or (
                existing_dept is not None
                and str(existing.department_id) != str(existing_dept.id)
            )
            changed = (
                existing.name != item.name
                or dept_id_changed
                or existing.is_special != item.is_special
            )
            if changed:
                preview_items.append(
                    WorkerBulkPreviewItem(
                        employee_no=item.employee_no,
                        name=item.name,
                        department_code=item.department_code,
                        action="update",
                        old_name=str(existing.name),
                        department_is_new=dept_is_new,
                    )
                )
                update_count += 1
            else:
                preview_items.append(
                    WorkerBulkPreviewItem(
                        employee_no=item.employee_no,
                        name=item.name,
                        department_code=item.department_code,
                        action="no_change",
                        department_is_new=False,
                    )
                )
                no_change_count += 1

    return WorkerBulkPreviewResponse(
        preview=preview_items,
        create_count=create_count,
        update_count=update_count,
        no_change_count=no_change_count,
        new_department_count=len(new_dept_codes),
    )


def bulk_upsert_workers(
    session: Session,
    tenant_id: str,
    items: list[WorkerBulkItem],
) -> WorkerBulkUpsertResponse:
    """Workerを一括登録・更新する（Upsert）、未登録の課を自動生成する.

    処理順:
    1. 課コードの解決と未登録課の自動生成
    2. 社員番号をキーにWorkerのUpsert

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        items: 登録・更新対象のWorkerアイテムリスト。

    Returns:
        作成・更新の件数、自動生成した課の件数と処理後のWorkerリスト。

    Raises:
        HTTPException: 重複するemployee_noが存在する場合（HTTP 422）。
        HTTPException: skill_rank_id が同一テナントに存在しない場合（HTTP 404）。
    """
    _validate_no_duplicate_employee_nos(items)

    # スキルランクの存在確認
    skill_rank_ids = list({item.skill_rank_id for item in items})
    for skill_rank_id in skill_rank_ids:
        _validate_skill_rank(session, tenant_id, skill_rank_id)

    # 課コードを解決し、未登録の課を自動生成
    dept_id_map, departments_created = _ensure_departments(session, tenant_id, items)

    # 既存Workerの取得
    employee_nos = [item.employee_no for item in items]
    existing_map = _fetch_workers_by_employee_nos(session, tenant_id, employee_nos)

    created = updated = 0
    result_items: list[Worker] = []

    for item in items:
        department_id = dept_id_map[item.department_code]
        existing = existing_map.get(item.employee_no)

        if existing is None:
            worker = Worker(
                tenant_id=tenant_id,
                employee_no=item.employee_no,
                name=item.name,
                department_id=department_id,
                skill_rank_id=item.skill_rank_id,
                is_special=item.is_special,
                joined_at=item.joined_at,
            )
            session.add(worker)
            created += 1
            result_items.append(worker)
        else:
            existing.name = item.name  # type: ignore[assignment]
            existing.department_id = department_id  # type: ignore[assignment]
            existing.skill_rank_id = item.skill_rank_id  # type: ignore[assignment]
            existing.is_special = item.is_special  # type: ignore[assignment]
            if item.joined_at is not None:
                existing.joined_at = item.joined_at  # type: ignore[assignment]
            session.add(existing)
            updated += 1
            result_items.append(existing)

    session.commit()
    for worker in result_items:
        session.refresh(worker)

    return WorkerBulkUpsertResponse(
        created=created,
        updated=updated,
        departments_created=departments_created,
        items=[WorkerResponse.model_validate(w) for w in result_items],
    )


def _validate_no_duplicate_employee_nos(items: list[WorkerBulkItem]) -> None:
    """リスト内の重複employee_noをチェックし、重複がある場合は例外を送出する."""
    nos = [item.employee_no for item in items]
    if len(nos) != len(set(nos)):
        seen: set[str] = set()
        duplicates: list[str] = []
        for no in nos:
            if no in seen:
                duplicates.append(no)
            seen.add(no)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"重複するemployee_noが含まれています: {', '.join(duplicates)}",
        )
