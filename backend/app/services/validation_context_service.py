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
    PlanStatusEnum,
    ShiftAssignment,
    ShiftPlan,
    ShiftRequirement,
    ShiftRequirementAssignment,
    ShiftSlot,
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
    start_date: date | None = None,
) -> ValidationContextResponse:
    """シフト作成画面マウント時の一括バリデーションコンテキストを返す.

    以下のデータを一括で集計・返却する:
    - テナントに属する全ワーカー一覧
    - 各ワーカーの当月日曜・祝日昼間シフト回数
    - 各ワーカーの前年GW・年末年始シフト参加回数
    - 各ワーカーの直近シフト日付（start_date 以降の published データも含む）

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        target_year_month: 対象年月（YYYY-MM形式）。
        start_date: 直近シフト日付を検索する際の開始日（省略時は制限なし）。
            フロントエンドから (月初日 - min_interval_days) として指定される。

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

    # 直近シフト日付を取得（published ShiftPlan のデータも含む）
    last_shift_dates = _get_last_shift_dates(
        session, tenant_id, worker_ids, start_date
    )

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
    start_date: date | None = None,
) -> dict[str, date]:
    """各ワーカーの直近のシフト日付を取得する（シフト間隔チェック用）.

    ShiftRequirementAssignment ベースの日付に加え、確定済み（published）
    ShiftPlan の ShiftSlot/ShiftAssignment から日付も取得してマージする。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        worker_ids: 対象ワーカーIDリスト。
        start_date: この日付以降のデータのみ検索する（省略時は全期間）。

    Returns:
        ワーカーIDの文字列 → 最新シフト日付のマップ。
    """
    if not worker_ids:
        return {}

    # ShiftRequirementAssignment ベースの日付を取得
    req_query = (
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
    )
    if start_date is not None:
        req_query = req_query.where(ShiftRequirement.shift_date >= start_date)

    req_rows = session.exec(
        req_query.order_by(ShiftRequirement.shift_date.desc())  # type: ignore[attr-defined]
    ).all()

    # ShiftSlot/ShiftAssignment ベースの日付を取得（confirmed: published のみ）
    slot_query = (
        select(
            ShiftAssignment.worker_id,
            ShiftSlot.date,
        )
        .join(ShiftSlot, ShiftAssignment.slot_id == ShiftSlot.id)  # type: ignore[arg-type]
        .join(ShiftPlan, ShiftPlan.id == ShiftSlot.plan_id)  # type: ignore[arg-type]
        .where(
            ShiftAssignment.tenant_id == tenant_id,
            ShiftAssignment.worker_id.in_(worker_ids),  # type: ignore[attr-defined]
            ShiftPlan.status == PlanStatusEnum.published,
        )
    )
    if start_date is not None:
        slot_query = slot_query.where(ShiftSlot.date >= start_date)

    slot_rows = session.exec(
        slot_query.order_by(ShiftSlot.date.desc())  # type: ignore[attr-defined]
    ).all()

    # 両方の結果をマージして各ワーカーの最新日付を決定
    last_dates: dict[str, date] = {}

    def _update(worker_id: object, raw_date: object) -> None:
        key = str(worker_id)
        if hasattr(raw_date, "date"):
            d: date = raw_date.date()  # type: ignore[union-attr]
        else:
            d = raw_date  # type: ignore[assignment]
        if key not in last_dates or d > last_dates[key]:
            last_dates[key] = d

    for worker_id, shift_date in req_rows:
        _update(worker_id, shift_date)

    for worker_id, slot_date in slot_rows:
        _update(worker_id, slot_date)

    return last_dates
