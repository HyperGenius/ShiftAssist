# backend/app/services/validation_context_service.py
"""シフト作成画面のバリデーションコンテキスト集計サービス層.

フロントエンドがシフト作成画面でリアルタイムバリデーションに必要なデータを
一括で集計・提供する。パフォーマンスを考慮してクエリ数を最小限に抑える。
"""

from datetime import date

from sqlmodel import Session, select

from app.models.models import (
    LongHolidayPeriod,
    LongHolidayTypeEnum,
    ShiftRequirement,
    ShiftRequirementAssignment,
    SlotTypeEnum,
    Worker,
)
from app.models.schemas import (
    ValidationContextResponse,
    ValidationContextWorkerStats,
    WorkerResponse,
)


def get_validation_context(
    session: Session,
    tenant_id: str,
    target_year_month: str,
) -> ValidationContextResponse:
    """シフト作成画面マウント時の一括バリデーションコンテキストを返す.

    以下のデータを一括で集計・返却する:
    - テナントに属する全ワーカー一覧
    - 各ワーカーの当月日曜・祝日昼間シフト回数
    - 各ワーカーの前年GW・年末年始シフト参加回数
    - 各ワーカーの直近シフト日付

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        target_year_month: 対象年月（YYYY-MM形式）。

    Returns:
        バリデーションコンテキストレスポンス。
    """
    # 対象年月を解析
    year, month = _parse_year_month(target_year_month)
    prev_year = year - 1

    # 全ワーカーを取得
    workers = session.exec(select(Worker).where(Worker.tenant_id == tenant_id)).all()

    worker_ids = [w.id for w in workers]

    # 当月の日曜・祝日昼間シフト回数を集計
    sun_hol_day_counts = _count_sun_hol_day_current_month(
        session, tenant_id, worker_ids, year, month
    )

    # 前年GW・年末年始シフト参加回数を集計
    gw_counts, year_end_counts = _count_long_holiday_prev_year(
        session, tenant_id, worker_ids, prev_year
    )

    # 直近シフト日付を取得
    last_shift_dates = _get_last_shift_dates(session, tenant_id, worker_ids)

    # ワーカー実績サマリーを構築
    worker_stats = []
    for worker in workers:
        wid = worker.id
        worker_stats.append(
            ValidationContextWorkerStats(
                worker_id=wid,  # type: ignore[arg-type]
                sun_hol_day_this_month=sun_hol_day_counts.get(str(wid), 0),
                gw_last_year=gw_counts.get(str(wid), 0),
                year_end_last_year=year_end_counts.get(str(wid), 0),
                last_shift_date=last_shift_dates.get(str(wid)),
            )
        )

    return ValidationContextResponse(
        workers=[WorkerResponse.model_validate(w) for w in workers],
        worker_stats=worker_stats,
    )


def _parse_year_month(target_year_month: str) -> tuple[int, int]:
    """YYYY-MM形式の文字列を (year, month) に変換する."""
    parts = target_year_month.split("-")
    return int(parts[0]), int(parts[1])


def _count_sun_hol_day_current_month(
    session: Session,
    tenant_id: str,
    worker_ids: list,
    year: int,
    month: int,
) -> dict[str, int]:
    """当月の日曜・祝日昼間（sun_hol_day）シフト回数をワーカーごとに集計する."""
    if not worker_ids:
        return {}

    # 対象月の開始日・終了日を計算
    import calendar

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    rows = session.exec(
        select(
            ShiftRequirementAssignment.worker_id,
        )
        .join(
            ShiftRequirement,
            ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
        )
        .where(
            ShiftRequirementAssignment.tenant_id == tenant_id,
            ShiftRequirementAssignment.worker_id.in_(worker_ids),  # type: ignore[attr-defined]
            ShiftRequirement.slot_type == SlotTypeEnum.sun_hol_day,
            ShiftRequirement.shift_date >= start_date,
            ShiftRequirement.shift_date <= end_date,
        )
    ).all()

    counts: dict[str, int] = {}
    for worker_id in rows:
        key = str(worker_id)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _count_long_holiday_prev_year(
    session: Session,
    tenant_id: str,
    worker_ids: list,
    prev_year: int,
) -> tuple[dict[str, int], dict[str, int]]:
    """前年のGWおよび年末年始のシフト参加回数をワーカーごとに集計する."""
    if not worker_ids:
        return {}, {}

    # 前年のGW・年末年始の期間を取得
    long_holiday_periods = session.exec(
        select(LongHolidayPeriod).where(
            LongHolidayPeriod.tenant_id == tenant_id,
            LongHolidayPeriod.year == prev_year,
            LongHolidayPeriod.holiday_type.in_(  # type: ignore[attr-defined]
                [LongHolidayTypeEnum.gw, LongHolidayTypeEnum.year_end]
            ),
        )
    ).all()

    gw_counts: dict[str, int] = {}
    year_end_counts: dict[str, int] = {}

    for period in long_holiday_periods:
        rows = session.exec(
            select(
                ShiftRequirementAssignment.worker_id,
            )
            .join(
                ShiftRequirement,
                ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
            )
            .where(
                ShiftRequirementAssignment.tenant_id == tenant_id,
                ShiftRequirementAssignment.worker_id.in_(worker_ids),  # type: ignore[attr-defined]
                ShiftRequirement.shift_date >= period.start_date,
                ShiftRequirement.shift_date <= period.end_date,
            )
        ).all()

        target_counts = (
            gw_counts
            if period.holiday_type == LongHolidayTypeEnum.gw
            else year_end_counts
        )
        for worker_id in rows:
            key = str(worker_id)
            target_counts[key] = target_counts.get(key, 0) + 1

    return gw_counts, year_end_counts


def _get_last_shift_dates(
    session: Session,
    tenant_id: str,
    worker_ids: list,
) -> dict[str, date]:
    """各ワーカーの直近のシフト日付を取得する（シフト間隔チェック用）."""
    if not worker_ids:
        return {}

    rows = session.exec(
        select(
            ShiftRequirementAssignment.worker_id,
            ShiftRequirement.shift_date,
        )
        .join(
            ShiftRequirement,
            ShiftRequirementAssignment.requirement_id == ShiftRequirement.id,  # type: ignore[arg-type]
        )
        .where(
            ShiftRequirementAssignment.tenant_id == tenant_id,
            ShiftRequirementAssignment.worker_id.in_(worker_ids),  # type: ignore[attr-defined]
        )
        .order_by(ShiftRequirement.shift_date.desc())  # type: ignore[attr-defined]
    ).all()

    last_dates: dict[str, date] = {}
    for worker_id, shift_date in rows:
        key = str(worker_id)
        if key not in last_dates:
            last_dates[key] = shift_date  # type: ignore[assignment]
    return last_dates
