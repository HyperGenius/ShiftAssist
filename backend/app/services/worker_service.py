# backend/app/services/worker_service.py
"""Worker CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import Department, TenantSkillRank, Worker
from app.models.schemas import WorkerCreate, WorkerResponse, WorkerUpdate


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

    worker = Worker(
        tenant_id=tenant_id,
        name=data.name,
        department_id=data.department_id,
        skill_rank_id=data.skill_rank_id,
        is_special=data.is_special,
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
