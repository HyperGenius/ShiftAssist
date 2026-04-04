# backend/app/routers/long_holiday_periods.py
"""LongHolidayPeriod CRUDルーター.

ベースパス: ``/api/long-holiday-periods``
すべてのエンドポイントはヘッダー ``X-Tenant-Id`` によるテナントアイソレーションが必須。
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.schemas import (
    LongHolidayPeriodCreate,
    LongHolidayPeriodResponse,
    LongHolidayPeriodUpdate,
)
from app.services import long_holiday_period_service

router = APIRouter(prefix="/api/long-holiday-periods", tags=["long-holiday-periods"])


@router.get("/", response_model=list[LongHolidayPeriodResponse])
def list_long_holiday_periods(
    year: int | None = Query(default=None, description="フィルタ対象の年"),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[LongHolidayPeriodResponse]:
    """テナントに属するLongHolidayPeriod一覧を取得する.

    Args:
        year: フィルタ対象の年（指定しない場合は全年取得）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        LongHolidayPeriod一覧。
    """
    return long_holiday_period_service.list_long_holiday_periods(
        session, tenant_id, year
    )


@router.post(
    "/",
    response_model=LongHolidayPeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_long_holiday_period(
    data: LongHolidayPeriodCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> LongHolidayPeriodResponse:
    """新しいLongHolidayPeriodを作成する.

    Args:
        data: LongHolidayPeriod作成リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成されたLongHolidayPeriodの情報。
    """
    return long_holiday_period_service.create_long_holiday_period(
        session, tenant_id, data
    )


@router.get("/{period_id}", response_model=LongHolidayPeriodResponse)
def get_long_holiday_period(
    period_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> LongHolidayPeriodResponse:
    """指定したLongHolidayPeriodを取得する.

    Args:
        period_id: 取得対象のLongHolidayPeriod ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        LongHolidayPeriodの情報。
    """
    return long_holiday_period_service.get_long_holiday_period(
        session, tenant_id, period_id
    )


@router.put("/{period_id}", response_model=LongHolidayPeriodResponse)
def update_long_holiday_period(
    period_id: uuid.UUID,
    data: LongHolidayPeriodUpdate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> LongHolidayPeriodResponse:
    """指定したLongHolidayPeriodを更新する.

    Args:
        period_id: 更新対象のLongHolidayPeriod ID。
        data: LongHolidayPeriod更新リクエストボディ。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        更新後のLongHolidayPeriodの情報。
    """
    return long_holiday_period_service.update_long_holiday_period(
        session, tenant_id, period_id, data
    )


@router.delete("/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_long_holiday_period(
    period_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したLongHolidayPeriodを物理削除する.

    Args:
        period_id: 削除対象のLongHolidayPeriod ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。
    """
    long_holiday_period_service.delete_long_holiday_period(
        session, tenant_id, period_id
    )
