# backend/app/routers/holidays.py
"""TenantHoliday CRUDルーター.

ベースパス: ``/api/holidays``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    TenantHolidayBulkCreate,
    TenantHolidayResponse,
)
from app.services import holiday_service

router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("/", response_model=list[TenantHolidayResponse])
def list_holidays(
    year: int | None = Query(None, description="フィルタ対象の年"),
    month: int | None = Query(None, ge=1, le=12, description="フィルタ対象の月（yearと組み合わせて使用）"),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[TenantHolidayResponse]:
    """テナントに属する休日一覧を取得する.

    ``year`` を指定した場合、その年のデータが未登録であれば日本の標準祝日を自動投入する。

    Args:
        year: フィルタ対象の年（省略時は全件）。
        month: フィルタ対象の月（``year`` と組み合わせて使用）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        休日一覧（日付昇順）。
    """
    return holiday_service.list_holidays(session, tenant_id, year=year, month=month)


@router.post(
    "/", response_model=list[TenantHolidayResponse], status_code=status.HTTP_201_CREATED
)
def create_holidays(
    data: TenantHolidayBulkCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[TenantHolidayResponse]:
    """休日を1件または複数件作成する.

    Args:
        data: 作成する休日データのリスト。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成された休日情報のリスト。
    """
    return holiday_service.create_holidays(session, tenant_id, data.holidays)


@router.delete("/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(
    holiday_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定した休日を削除する.

    Args:
        holiday_id: 削除対象の休日ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    holiday_service.delete_holiday(session, tenant_id, holiday_id)
