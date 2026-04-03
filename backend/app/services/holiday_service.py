# backend/app/services/holiday_service.py
"""TenantHoliday CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
対象年のデータが未登録の場合は ``jpholiday`` を用いて日本の標準祝日を自動投入する。
"""

import calendar
import uuid
from datetime import date

import jpholiday
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import TenantHoliday
from app.models.schemas import (
    TenantHolidayCreate,
    TenantHolidayResponse,
)

_jp_holiday = jpholiday.JPHoliday()


def _seed_year_holidays(session: Session, tenant_id: str, year: int) -> None:
    """指定した年の日本標準祝日をDBに投入する.

    既存レコードがある場合はスキップ（UniqueConstraint に依存しない safe な実装）。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        year: シーディング対象の年。
    """
    holidays = _jp_holiday.year_holidays(year)
    for h in holidays:
        existing = session.exec(
            select(TenantHoliday).where(
                TenantHoliday.tenant_id == tenant_id,
                TenantHoliday.date == h.date,
            )
        ).first()
        if existing is None:
            session.add(
                TenantHoliday(
                    tenant_id=tenant_id,
                    date=h.date,
                    name=h.name,
                    is_long_holiday=False,
                )
            )
    session.commit()


def list_holidays(
    session: Session,
    tenant_id: str,
    year: int | None = None,
    month: int | None = None,
) -> list[TenantHolidayResponse]:
    """テナントに属する休日一覧を取得する.

    対象年が指定されていて、その年のデータが1件も存在しない場合は
    日本の標準祝日を自動的にDBへ投入してから返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        year: フィルタ対象の年（省略時は全件）。
        month: フィルタ対象の月（yearと組み合わせて使用）。

    Returns:
        TenantHolidayレスポンスモデルのリスト（日付昇順）。
    """
    stmt = select(TenantHoliday).where(TenantHoliday.tenant_id == tenant_id)

    if year is not None:
        # 対象年のデータが未存在の場合は自動シーディング
        year_records = session.exec(
            select(TenantHoliday).where(
                TenantHoliday.tenant_id == tenant_id,
                TenantHoliday.date >= date(year, 1, 1),
                TenantHoliday.date <= date(year, 12, 31),
            )
        ).all()
        if len(year_records) == 0:
            _seed_year_holidays(session, tenant_id, year)

        stmt = stmt.where(
            TenantHoliday.date >= date(year, 1, 1),
            TenantHoliday.date <= date(year, 12, 31),
        )

        if month is not None:
            last_day_of_month = calendar.monthrange(year, month)[1]
            stmt = stmt.where(
                TenantHoliday.date >= date(year, month, 1),
                TenantHoliday.date <= date(year, month, last_day_of_month),
            )

    stmt = stmt.order_by(TenantHoliday.date)  # type: ignore[arg-type]
    rows = session.exec(stmt).all()
    return [TenantHolidayResponse.model_validate(r) for r in rows]


def create_holidays(
    session: Session,
    tenant_id: str,
    holidays: list[TenantHolidayCreate],
) -> list[TenantHolidayResponse]:
    """1件または複数の休日レコードを作成する.

    同一テナント・同一日付のレコードが既に存在する場合は 409 を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        holidays: 作成する休日データのリスト。

    Returns:
        作成されたTenantHolidayレスポンスモデルのリスト。

    Raises:
        HTTPException: 同一日付のレコードが既に存在する場合（409）。
    """
    # 重複チェック
    for h in holidays:
        existing = session.exec(
            select(TenantHoliday).where(
                TenantHoliday.tenant_id == tenant_id,
                TenantHoliday.date == h.date,
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Holiday on '{h.date}' already exists for this tenant.",
            )

    created = []
    for h in holidays:
        record = TenantHoliday(
            tenant_id=tenant_id,
            date=h.date,
            name=h.name,
            is_long_holiday=h.is_long_holiday,
        )
        session.add(record)
        created.append(record)

    session.commit()
    for r in created:
        session.refresh(r)

    return [TenantHolidayResponse.model_validate(r) for r in created]


def delete_holiday(
    session: Session,
    tenant_id: str,
    holiday_id: uuid.UUID,
) -> None:
    """指定した休日レコードを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        holiday_id: 削除対象の休日ID。

    Raises:
        HTTPException: 対象レコードが存在しない場合（404）。
    """
    record = session.exec(
        select(TenantHoliday).where(
            TenantHoliday.id == holiday_id,  # type: ignore[arg-type]
            TenantHoliday.tenant_id == tenant_id,
        )
    ).first()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holiday '{holiday_id}' not found.",
        )
    session.delete(record)
    session.commit()

