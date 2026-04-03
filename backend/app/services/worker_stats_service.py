# backend/app/services/worker_stats_service.py
"""ワーカー勤務実績統計集計サービス層.

``published`` 状態のシフトプランに基づき、ワーカーごとの枠種別勤務回数と
在籍期間を考慮した月平均値を集計・提供する。
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.models import (
    PlanStatusEnum,
    ShiftAssignment,
    ShiftPlan,
    ShiftSlot,
    SlotTypeEnum,
    TenantStatsConfig,
    Worker,
)
from app.models.schemas import (
    TenantStatsConfigResponse,
    TenantWorkerStatsResponse,
    WorkerSlotStats,
    WorkerStatsResponse,
)

# 休日扱いの枠種別（休日勤務の偏り検知対象）
_HOLIDAY_SLOT_TYPES = {
    SlotTypeEnum.sat_day,
    SlotTypeEnum.sat_night,
    SlotTypeEnum.sun_hol_day,
    SlotTypeEnum.sun_hol_night,
    SlotTypeEnum.long_hol_day,
    SlotTypeEnum.long_hol_night,
}

_DEFAULT_STATS_PERIOD_MONTHS = 12


def get_stats_config(session: Session, tenant_id: str) -> TenantStatsConfigResponse:
    """テナントの統計設定を返す.

    DBにテナント固有の設定が保存されている場合はそれを返し、
    存在しない場合はデフォルト値（12ヶ月）を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。

    Returns:
        テナント統計設定レスポンス。
    """
    config = session.exec(
        select(TenantStatsConfig).where(
            TenantStatsConfig.tenant_id == tenant_id  # type: ignore[arg-type]
        )
    ).first()

    if config is None:
        return TenantStatsConfigResponse(
            tenant_id=tenant_id,
            stats_period_months=_DEFAULT_STATS_PERIOD_MONTHS,
        )

    return TenantStatsConfigResponse.model_validate(config)


def update_stats_config(
    session: Session,
    tenant_id: str,
    stats_period_months: int,
) -> TenantStatsConfigResponse:
    """テナントの統計設定を更新（upsert）する.

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        stats_period_months: 統計集計対象期間（月数）。

    Returns:
        更新後のテナント統計設定レスポンス。
    """
    config = session.exec(
        select(TenantStatsConfig).where(
            TenantStatsConfig.tenant_id == tenant_id  # type: ignore[arg-type]
        )
    ).first()

    if config is None:
        config = TenantStatsConfig(
            tenant_id=tenant_id,
            stats_period_months=stats_period_months,
        )
        session.add(config)
    else:
        config.stats_period_months = stats_period_months
        config.updated_at = datetime.now(UTC)

    session.commit()
    session.refresh(config)
    return TenantStatsConfigResponse.model_validate(config)


def _compute_effective_months(
    joined_at: date | None, stats_period_months: int, today: date
) -> float:
    """在籍期間と集計期間の短い方を有効在籍月数として計算する.

    Args:
        joined_at: ワーカーの着任日。Noneの場合は集計期間全体を使用。
        stats_period_months: テナントの統計集計期間（月数）。
        today: 計算基準日。

    Returns:
        有効在籍月数（小数点以下あり）。最低値は1.0。
    """
    if joined_at is None:
        return float(stats_period_months)

    days_since_joined = (today - joined_at).days
    months_since_joined = days_since_joined / 30.44  # 平均月日数で割る
    effective = min(float(stats_period_months), months_since_joined)
    return max(effective, 1.0)


def _build_stats_response(
    worker: Worker,
    count_by_slot: dict[str, int],
    effective_months: float,
) -> WorkerStatsResponse:
    """ワーカーの統計レスポンスを構築する.

    Args:
        worker: ワーカーORMオブジェクト。
        count_by_slot: 枠種別ごとの勤務回数マップ。
        effective_months: 有効在籍月数。

    Returns:
        WorkerStatsResponse。
    """
    slot_stats = [
        WorkerSlotStats(
            slot_type=slot_type,
            count=count_by_slot.get(slot_type.value, 0),
            monthly_avg=count_by_slot.get(slot_type.value, 0) / effective_months,
        )
        for slot_type in SlotTypeEnum
    ]

    holiday_count = sum(count_by_slot.get(s.value, 0) for s in _HOLIDAY_SLOT_TYPES)
    holiday_monthly_avg = holiday_count / effective_months

    return WorkerStatsResponse(
        worker_id=worker.id,
        worker_name=worker.name,
        effective_months=effective_months,
        slot_stats=slot_stats,
        holiday_slot_monthly_avg=holiday_monthly_avg,
    )


def get_worker_stats(
    session: Session,
    tenant_id: str,
    worker_id: uuid.UUID,
) -> WorkerStatsResponse:
    """指定ワーカーの勤務実績統計を取得する.

    ``published`` ステータスのシフトプランのみを集計対象とする。
    集計期間はテナント設定に基づき、着任日との比較で有効期間を算出する。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        worker_id: 集計対象のワーカーID。

    Returns:
        ワーカーの統計レスポンス。

    Raises:
        HTTPException: ワーカーが存在しない場合。
    """
    from fastapi import HTTPException, status

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

    stats_config = get_stats_config(session, tenant_id)
    stats_period_months = stats_config.stats_period_months

    today = datetime.now(UTC).date()
    cutoff_year = today.year - (stats_period_months // 12)
    cutoff_month = today.month - (stats_period_months % 12)
    if cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff_ym = f"{cutoff_year:04d}-{cutoff_month:02d}"

    rows = session.exec(
        select(ShiftSlot.slot_type, func.count(ShiftAssignment.id).label("cnt"))
        .join(ShiftAssignment, ShiftAssignment.slot_id == ShiftSlot.id)
        .join(ShiftPlan, ShiftPlan.id == ShiftSlot.plan_id)
        .where(
            ShiftAssignment.worker_id == worker_id,  # type: ignore[arg-type]
            ShiftPlan.tenant_id == tenant_id,
            ShiftPlan.status == PlanStatusEnum.published,
            ShiftPlan.target_year_month >= cutoff_ym,
        )
        .group_by(ShiftSlot.slot_type)
    ).all()

    count_by_slot: dict[str, int] = {str(row[0]): row[1] for row in rows}

    effective_months = _compute_effective_months(
        worker.joined_at, stats_period_months, today
    )

    return _build_stats_response(worker, count_by_slot, effective_months)


def get_all_worker_stats(
    session: Session,
    tenant_id: str,
) -> TenantWorkerStatsResponse:
    """テナント内の全ワーカーの勤務実績統計を一括取得する.

    ``published`` ステータスのシフトプランのみを集計対象とする。
    集計期間はテナント設定に基づき、着任日との比較で有効期間を算出する。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。

    Returns:
        テナント全ワーカーの統計一括レスポンス。
    """
    stats_config = get_stats_config(session, tenant_id)
    stats_period_months = stats_config.stats_period_months

    today = datetime.now(UTC).date()
    cutoff_year = today.year - (stats_period_months // 12)
    cutoff_month = today.month - (stats_period_months % 12)
    if cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff_ym = f"{cutoff_year:04d}-{cutoff_month:02d}"

    workers = session.exec(select(Worker).where(Worker.tenant_id == tenant_id)).all()

    if not workers:
        return TenantWorkerStatsResponse(
            stats_period_months=stats_period_months,
            items=[],
        )

    worker_ids = [w.id for w in workers]

    rows = session.exec(
        select(
            ShiftAssignment.worker_id,
            ShiftSlot.slot_type,
            func.count(ShiftAssignment.id).label("cnt"),
        )
        .join(ShiftSlot, ShiftAssignment.slot_id == ShiftSlot.id)
        .join(ShiftPlan, ShiftPlan.id == ShiftSlot.plan_id)
        .where(
            ShiftAssignment.worker_id.in_(worker_ids),  # type: ignore[union-attr]
            ShiftPlan.tenant_id == tenant_id,
            ShiftPlan.status == PlanStatusEnum.published,
            ShiftPlan.target_year_month >= cutoff_ym,
        )
        .group_by(ShiftAssignment.worker_id, ShiftSlot.slot_type)
    ).all()

    counts_map: dict[uuid.UUID, dict[str, int]] = {}
    for row in rows:
        wid = row[0]
        slot_type = str(row[1])
        cnt = row[2]
        if wid not in counts_map:
            counts_map[wid] = {}
        counts_map[wid][slot_type] = cnt

    items = []
    for worker in workers:
        count_by_slot = counts_map.get(worker.id, {})
        effective_months = _compute_effective_months(
            worker.joined_at, stats_period_months, today
        )
        items.append(_build_stats_response(worker, count_by_slot, effective_months))

    return TenantWorkerStatsResponse(
        stats_period_months=stats_period_months,
        items=items,
    )
