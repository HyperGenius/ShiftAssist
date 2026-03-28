# backend/app/dependencies.py
"""FastAPI共通依存関数."""

from fastapi import Header, HTTPException, status


def get_tenant_id(x_tenant_id: str = Header(...)) -> str:
    """リクエストヘッダーからテナントIDを取得する依存関数.

    すべてのAPIエンドポイントでテナントアイソレーションを実現するために使用する。
    ヘッダー ``X-Tenant-Id`` が存在しない場合は 422 を返す。

    Args:
        x_tenant_id: HTTPヘッダー ``X-Tenant-Id`` の値（Clerk Organization ID）。

    Returns:
        テナントID文字列。

    Raises:
        HTTPException: ``X-Tenant-Id`` ヘッダーが空文字列の場合。
    """
    if not x_tenant_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-Tenant-Id header must not be empty.",
        )
    return x_tenant_id
