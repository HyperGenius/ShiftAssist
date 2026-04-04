# backend/app/services/long_holiday_period_service.py
"""LongHolidayPeriod CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import LongHolidayPeriod, LongHolidayTypeEnum
from app.models.schemas import (
    LongHolidayPeriodCreate,
    LongHolidayPeriodResponse,
    LongHolidayPeriodUpdate,
)


def create_long_holiday_period(
    session: Session, tenant_id: str, data: LongHolidayPeriodCreate
) -> LongHolidayPeriodResponse:
    """新しいLongHolidayPeriodを作成する.

    同一テナント・同一種別・同一年のレコードは1件のみ許容される。

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: LongHolidayPeriod作成リクエストデータ。

    Returns:
        作成されたLongHolidayPeriodのレスポンスモデル。

    Raises:
        HTTPException: 同一種別・同一年のレコードが既に存在する場合。
    """
    existing = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.tenant_id == tenant_id,
            LongHolidayPeriod.holiday_type == data.holiday_type,
            LongHolidayPeriod.year == data.year,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"LongHolidayPeriod for type '{data.holiday_type}' "
                f"and year {data.year} already exists."
            ),
        )

    period = LongHolidayPeriod(
        tenant_id=tenant_id,
        holiday_type=data.holiday_type,
        year=data.year,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    session.add(period)
    session.commit()
    session.refresh(period)
    return LongHolidayPeriodResponse.model_validate(period)


def list_long_holiday_periods(
    session: Session, tenant_id: str, year: int | None = None
) -> list[LongHolidayPeriodResponse]:
    """テナントに属するLongHolidayPeriod一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        year: フィルタ対象の年（指定しない場合は全年取得）。

    Returns:
        LongHolidayPeriod一覧のレスポンスモデルリスト。
    """
    stmt = select(LongHolidayPeriod).where(LongHolidayPeriod.tenant_id == tenant_id)
    if year is not None:
        stmt = stmt.where(LongHolidayPeriod.year == year)
    periods = session.exec(stmt).all()
    return [LongHolidayPeriodResponse.model_validate(p) for p in periods]


def get_long_holiday_period(
    session: Session, tenant_id: str, period_id: uuid.UUID
) -> LongHolidayPeriodResponse:
    """指定したLongHolidayPeriodを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        period_id: 取得対象のLongHolidayPeriod ID。

    Returns:
        LongHolidayPeriodレスポンスモデル。

    Raises:
        HTTPException: LongHolidayPeriodが存在しない場合。
    """
    period = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.id == period_id,  # type: ignore[arg-type]
            LongHolidayPeriod.tenant_id == tenant_id,
        )
    ).first()
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LongHolidayPeriod '{period_id}' not found.",
        )
    return LongHolidayPeriodResponse.model_validate(period)


def update_long_holiday_period(
    session: Session,
    tenant_id: str,
    period_id: uuid.UUID,
    data: LongHolidayPeriodUpdate,
) -> LongHolidayPeriodResponse:
    """指定したLongHolidayPeriodを更新する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        period_id: 更新対象のLongHolidayPeriod ID。
        data: LongHolidayPeriod更新リクエストデータ。

    Returns:
        更新後のLongHolidayPeriodレスポンスモデル。

    Raises:
        HTTPException: LongHolidayPeriodが存在しない場合。
    """
    period = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.id == period_id,  # type: ignore[arg-type]
            LongHolidayPeriod.tenant_id == tenant_id,
        )
    ).first()
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LongHolidayPeriod '{period_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(period, field, value)

    session.add(period)
    session.commit()
    session.refresh(period)
    return LongHolidayPeriodResponse.model_validate(period)


def delete_long_holiday_period(
    session: Session, tenant_id: str, period_id: uuid.UUID
) -> None:
    """指定したLongHolidayPeriodを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        period_id: 削除対象のLongHolidayPeriod ID。

    Raises:
        HTTPException: LongHolidayPeriodが存在しない場合。
    """
    period = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.id == period_id,  # type: ignore[arg-type]
            LongHolidayPeriod.tenant_id == tenant_id,
        )
    ).first()
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LongHolidayPeriod '{period_id}' not found.",
        )
    session.delete(period)
    session.commit()


def get_period_for_date(
    session: Session,
    tenant_id: str,
    target_date: object,
) -> LongHolidayPeriod | None:
    """指定された日付が属する長期休暇期間を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        target_date: 検索対象の日付。

    Returns:
        該当するLongHolidayPeriodオブジェクト、または None。
    """
    from datetime import date as date_type

    d: date_type = target_date  # type: ignore[assignment]
    periods = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.tenant_id == tenant_id,
            LongHolidayPeriod.start_date <= d,  # type: ignore[arg-type]
            LongHolidayPeriod.end_date >= d,  # type: ignore[arg-type]
        )
    ).all()
    return periods[0] if periods else None


def is_holiday_type_excluded_by_position(
    holiday_type: LongHolidayTypeEnum, position: object
) -> bool:
    """長期休暇種別と役職の除外フラグを照らし合わせてアサイン除外か判定する.

    Args:
        holiday_type: 長期休暇の種別。
        position: Positionオブジェクト。

    Returns:
        除外される場合True。
    """
    from app.models.models import Position

    p: Position = position  # type: ignore[assignment]
    if p.is_excluded_from_all_shifts:
        return True
    if holiday_type == LongHolidayTypeEnum.gw and p.is_excluded_from_gw:
        return True
    if holiday_type == LongHolidayTypeEnum.sw and p.is_excluded_from_sw:
        return True
    if holiday_type == LongHolidayTypeEnum.year_end and p.is_excluded_from_year_end:
        return True
    return False
