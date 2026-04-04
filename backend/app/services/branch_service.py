# backend/app/services/branch_service.py
"""Branch CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import Branch
from app.models.schemas import BranchCreate, BranchResponse, BranchUpdate


def create_branch(
    session: Session, tenant_id: str, data: BranchCreate
) -> BranchResponse:
    """新しいBranchを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: Branch作成リクエストデータ。

    Returns:
        作成されたBranchのレスポンスモデル。

    Raises:
        HTTPException: 同じコードのBranchが既に存在する場合。
    """
    existing = session.exec(
        select(Branch).where(
            Branch.tenant_id == tenant_id,
            Branch.code == data.code,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Branch with code '{data.code}' already exists.",
        )

    branch = Branch(
        tenant_id=tenant_id,
        name=data.name,
        code=data.code,
    )
    session.add(branch)
    session.commit()
    session.refresh(branch)
    return BranchResponse.model_validate(branch)


def list_branches(session: Session, tenant_id: str) -> list[BranchResponse]:
    """テナントに属するBranch一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        Branch一覧のレスポンスモデルリスト。
    """
    branches = session.exec(select(Branch).where(Branch.tenant_id == tenant_id)).all()
    return [BranchResponse.model_validate(b) for b in branches]


def get_branch(
    session: Session, tenant_id: str, branch_id: uuid.UUID
) -> BranchResponse:
    """指定したBranchを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        branch_id: 取得対象のBranch ID。

    Returns:
        Branchレスポンスモデル。

    Raises:
        HTTPException: Branchが存在しない場合。
    """
    branch = session.exec(
        select(Branch).where(
            Branch.id == branch_id,  # type: ignore[arg-type]
            Branch.tenant_id == tenant_id,
        )
    ).first()
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch '{branch_id}' not found.",
        )
    return BranchResponse.model_validate(branch)


def update_branch(
    session: Session,
    tenant_id: str,
    branch_id: uuid.UUID,
    data: BranchUpdate,
) -> BranchResponse:
    """指定したBranchを更新する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        branch_id: 更新対象のBranch ID。
        data: Branch更新リクエストデータ。

    Returns:
        更新後のBranchレスポンスモデル。

    Raises:
        HTTPException: Branchが存在しない場合。
    """
    branch = session.exec(
        select(Branch).where(
            Branch.id == branch_id,  # type: ignore[arg-type]
            Branch.tenant_id == tenant_id,
        )
    ).first()
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch '{branch_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)

    session.add(branch)
    session.commit()
    session.refresh(branch)
    return BranchResponse.model_validate(branch)


def delete_branch(session: Session, tenant_id: str, branch_id: uuid.UUID) -> None:
    """指定したBranchを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        branch_id: 削除対象のBranch ID。

    Raises:
        HTTPException: Branchが存在しない場合。
    """
    branch = session.exec(
        select(Branch).where(
            Branch.id == branch_id,  # type: ignore[arg-type]
            Branch.tenant_id == tenant_id,
        )
    ).first()
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Branch '{branch_id}' not found.",
        )
    session.delete(branch)
    session.commit()
