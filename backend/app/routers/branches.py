# backend/app/routers/branches.py
"""Branch CRUDルーター.

ベースパス: ``/api/branches``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import BranchCreate, BranchResponse, BranchUpdate
from app.services import branch_service

router = APIRouter(prefix="/api/branches", tags=["branches"])


@router.get("/", response_model=list[BranchResponse])
def list_branches(
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[BranchResponse]:
    """テナントに属するBranch一覧を取得する.

    Args:
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Branch一覧。
    """
    return branch_service.list_branches(session, tenant_id)


@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    data: BranchCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> BranchResponse:
    """新しいBranchを作成する.

    Args:
        data: Branch作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたBranchの情報。
    """
    return branch_service.create_branch(session, tenant_id, data)


@router.get("/{branch_id}", response_model=BranchResponse)
def get_branch(
    branch_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> BranchResponse:
    """指定したBranchを取得する.

    Args:
        branch_id: 取得対象のBranch ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        Branchの情報。
    """
    return branch_service.get_branch(session, tenant_id, branch_id)


@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: uuid.UUID,
    data: BranchUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> BranchResponse:
    """指定したBranchを更新する.

    Args:
        branch_id: 更新対象のBranch ID。
        data: Branch更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のBranchの情報。
    """
    return branch_service.update_branch(session, tenant_id, branch_id, data)


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したBranchを物理削除する.

    Args:
        branch_id: 削除対象のBranch ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    branch_service.delete_branch(session, tenant_id, branch_id)
