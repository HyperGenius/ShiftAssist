# backend/app/services/shift_verify_service.py
"""シフトVerify（Before/After 集計差分）サービス層.

``ShiftPlan`` に紐づく ``ShiftSlot`` / ``ShiftAssignment`` から
新シフト適用前後の Worker 別・SlotType 別アサイン偏りを算出する。
DB への書き込みは行わない（参照専用）。
"""

import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.models import (
    Department,
    EmploymentType,
    Position,
    ShiftAssignment,
    ShiftPlan,
    ShiftSlot,
    SlotTypeEnum,
    TenantSkillRank,
    Worker,
    WorkerMonthlySlotStats,
)
from app.models.schemas import (
    ShiftVerifyResponse,
    ShiftVerifySlotStat,
    ShiftVerifyWeekdayDelta,
    ShiftVerifyWorkerItem,
)
from app.services.worker_stats_service import (
    _compute_aggregate_cutoff,
    _compute_effective_months_for_aggregate,
    _resolve_worker_attributes,
)


def _prev_month_ym(year_month: str) -> str:
    """指定年月の 1 ヶ月前の年月文字列を返す.

    Args:
        year_month: 年月文字列（YYYY-MM形式）。

    Returns:
        1 ヶ月前の年月文字列（YYYY-MM形式）。
    """
    y, m = int(year_month[:4]), int(year_month[5:7])
    m -= 1
    if m == 0:
        m = 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def get_shift_verify_stats(
    session: Session,
    tenant_id: str,
    shift_plan_id: uuid.UUID,
) -> ShiftVerifyResponse:
    """シフトプランの Before/After 集計差分を返す.

    - **Before**: シフトプラン対象月の 1 ヶ月前を末月とした直近 12 ヶ月
    - **After**: シフトプラン対象月を末月とした直近 12 ヶ月
      (= Before 集計ベース + 今回のシフトプランのアサイン)

    DB への書き込みは行わない（参照のみ）。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        shift_plan_id: 検証対象のシフトプランID。

    Returns:
        ShiftVerifyResponse。

    Raises:
        HTTPException 404: 指定された shift_plan_id が存在しない場合。
    """
    # 1. ShiftPlan を取得（テナント分離）
    plan = session.exec(
        select(ShiftPlan).where(
            ShiftPlan.id == shift_plan_id,  # type: ignore[arg-type]
            ShiftPlan.tenant_id == tenant_id,
        )
    ).first()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ShiftPlan '{shift_plan_id}' not found.",
        )

    year_month: str = str(plan.target_year_month)  # e.g. "2026-06"

    # 2. Before / After 期間を算出
    # Before: year_month の 1 ヶ月前を末月とした直近 12 ヶ月
    before_end_ym = _prev_month_ym(year_month)  # e.g. "2026-05"
    before_start_ym, _ = _compute_aggregate_cutoff(before_end_ym)  # e.g. "2025-06"

    # After: year_month を末月とした直近 12 ヶ月
    after_end_ym = year_month  # e.g. "2026-06"
    after_start_ym, _ = _compute_aggregate_cutoff(after_end_ym)  # e.g. "2025-07"

    before_period_str = f"{before_start_ym} 〜 {before_end_ym}"
    after_period_str = f"{after_start_ym} 〜 {after_end_ym}"

    # 3. Workers の一括取得
    workers = session.exec(
        select(Worker).where(Worker.tenant_id == tenant_id)
    ).all()

    if not workers:
        return ShiftVerifyResponse(
            year_month=year_month,
            before_period=before_period_str,
            after_period=after_period_str,
            items=[],
        )

    worker_ids = [w.id for w in workers]

    # --- 関連テーブルをバッチクエリで一括取得（N+1回避） ---
    positions = session.exec(
        select(Position).where(Position.tenant_id == tenant_id)
    ).all()
    position_map: dict[uuid.UUID, str] = {p.id: p.name for p in positions}  # type: ignore[misc]

    departments = session.exec(
        select(Department).where(Department.tenant_id == tenant_id)
    ).all()
    department_map: dict[uuid.UUID, str] = {d.id: d.name for d in departments}  # type: ignore[misc]

    skill_ranks = session.exec(
        select(TenantSkillRank).where(TenantSkillRank.tenant_id == tenant_id)
    ).all()
    skill_rank_map: dict[uuid.UUID, str] = {s.id: s.name for s in skill_ranks}  # type: ignore[misc]

    employment_types = session.exec(
        select(EmploymentType).where(EmploymentType.tenant_id == tenant_id)
    ).all()
    employment_type_map: dict[uuid.UUID, tuple[str, bool]] = {
        e.id: (e.name, bool(e.is_default))  # type: ignore[misc]
        for e in employment_types
    }

    # 4. Before 集計: worker_monthly_slot_stats から [before_start..before_end] を取得
    before_rows = session.exec(
        select(
            WorkerMonthlySlotStats.worker_id,
            WorkerMonthlySlotStats.slot_type,
            WorkerMonthlySlotStats.weekday,
            func.sum(WorkerMonthlySlotStats.count).label("total"),
        )
        .where(
            WorkerMonthlySlotStats.tenant_id == tenant_id,
            WorkerMonthlySlotStats.worker_id.in_(worker_ids),  # type: ignore[union-attr]
            WorkerMonthlySlotStats.year_month >= before_start_ym,
            WorkerMonthlySlotStats.year_month <= before_end_ym,
        )
        .group_by(
            WorkerMonthlySlotStats.worker_id,
            WorkerMonthlySlotStats.slot_type,
            WorkerMonthlySlotStats.weekday,
        )
    ).all()

    # worker_id → slot_type → weekday → count
    before_counts_map: dict[uuid.UUID, dict[str, dict[int | None, int]]] = {}
    for row in before_rows:
        wid: uuid.UUID = row[0]
        slot_type_key = str(row[1])
        weekday: int | None = row[2]
        total = int(row[3])
        before_counts_map.setdefault(wid, {}).setdefault(slot_type_key, {})[weekday] = total

    # 5. After ベース集計: [after_start..before_end] (= 12 ヶ月 - 1 ヶ月)
    #    after_start 〜 before_end は year_month を除く 11 ヶ月分
    after_base_rows = session.exec(
        select(
            WorkerMonthlySlotStats.worker_id,
            WorkerMonthlySlotStats.slot_type,
            WorkerMonthlySlotStats.weekday,
            func.sum(WorkerMonthlySlotStats.count).label("total"),
        )
        .where(
            WorkerMonthlySlotStats.tenant_id == tenant_id,
            WorkerMonthlySlotStats.worker_id.in_(worker_ids),  # type: ignore[union-attr]
            WorkerMonthlySlotStats.year_month >= after_start_ym,
            WorkerMonthlySlotStats.year_month <= before_end_ym,
        )
        .group_by(
            WorkerMonthlySlotStats.worker_id,
            WorkerMonthlySlotStats.slot_type,
            WorkerMonthlySlotStats.weekday,
        )
    ).all()

    after_counts_map: dict[uuid.UUID, dict[str, dict[int | None, int]]] = {}
    for row in after_base_rows:
        wid = row[0]
        slot_type_key = str(row[1])
        weekday = row[2]
        total = int(row[3])
        after_counts_map.setdefault(wid, {}).setdefault(slot_type_key, {})[weekday] = total

    # 6. シフトプランのアサインメントを After カウントに加算
    # 6a. weekday_night 以外: 曜日不問（weekday=None）
    non_wn_plan_rows = session.exec(
        select(
            ShiftAssignment.worker_id,
            ShiftSlot.slot_type,
            func.count(ShiftAssignment.id).label("cnt"),
        )
        .join(ShiftSlot, ShiftAssignment.slot_id == ShiftSlot.id)
        .where(
            ShiftSlot.plan_id == plan.id,
            ShiftSlot.slot_type != SlotTypeEnum.weekday_night,
            ShiftAssignment.worker_id.isnot(None),  # type: ignore[union-attr]
        )
        .group_by(ShiftAssignment.worker_id, ShiftSlot.slot_type)
    ).all()

    for row in non_wn_plan_rows:
        wid = row[0]
        slot_type_key = str(row[1])
        cnt = int(row[2])
        wd_map = after_counts_map.setdefault(wid, {}).setdefault(slot_type_key, {})
        wd_map[None] = wd_map.get(None, 0) + cnt

    # 6b. weekday_night: isodow 単位で集計し月〜木(0〜3) / その他(None) に分類
    wn_plan_rows = session.exec(
        select(
            ShiftAssignment.worker_id,
            func.extract("isodow", ShiftSlot.date).label("isodow"),
            func.count(ShiftAssignment.id).label("cnt"),
        )
        .join(ShiftSlot, ShiftAssignment.slot_id == ShiftSlot.id)
        .where(
            ShiftSlot.plan_id == plan.id,
            ShiftSlot.slot_type == SlotTypeEnum.weekday_night,
            ShiftAssignment.worker_id.isnot(None),  # type: ignore[union-attr]
        )
        .group_by(
            ShiftAssignment.worker_id,
            func.extract("isodow", ShiftSlot.date),
        )
    ).all()

    for row in wn_plan_rows:
        wid = row[0]
        isodow = int(row[1]) if row[1] is not None else None
        cnt = int(row[2])
        # isodow 1〜4 → weekday 0〜3（月〜木）, 5〜7 → None
        weekday = (isodow - 1) if (isodow is not None and 1 <= isodow <= 4) else None
        slot_type_key = SlotTypeEnum.weekday_night.value
        wd_map = after_counts_map.setdefault(wid, {}).setdefault(slot_type_key, {})
        wd_map[weekday] = wd_map.get(weekday, 0) + cnt

    # 7. After 月平均を全 Worker 分計算（outlier 判定用）
    # worker_id → slot_type_value → after_monthly_avg（全 weekday 合計ベース）
    after_avgs: dict[uuid.UUID, dict[str, float]] = {}
    for worker in workers:
        wid = worker.id  # type: ignore[assignment]
        after_eff = _compute_effective_months_for_aggregate(
            worker.joined_at,  # type: ignore[arg-type]
            after_start_ym,
            after_end_ym,
        )
        worker_after = after_counts_map.get(wid, {})
        after_avgs[wid] = {}
        for slot_type in SlotTypeEnum:
            slot_counts = worker_after.get(slot_type.value, {})
            total = sum(slot_counts.values())
            after_avgs[wid][slot_type.value] = total / after_eff

    # 8. Outlier 閾値: slot_type ごとに全 Worker の After 月平均の mean + 1σ
    # サンプル標準偏差（n-1 除算）を使用し、Worker 数が少ない場合の精度を確保する
    outlier_thresholds: dict[str, float] = {}
    for slot_type in SlotTypeEnum:
        avgs = [after_avgs[w.id][slot_type.value] for w in workers]  # type: ignore[index]
        n = len(avgs)
        if n > 1:
            mean = sum(avgs) / n
            # サンプル分散（不偏分散）: n-1 で除算
            variance = sum((a - mean) ** 2 for a in avgs) / (n - 1)
            std = math.sqrt(variance)
            outlier_thresholds[slot_type.value] = mean + std
        else:
            # Worker が 1 名以下の場合は outlier 判定不能
            outlier_thresholds[slot_type.value] = math.inf

    # 9. ShiftVerifyWorkerItem を構築
    items = []
    for worker in workers:
        wid = worker.id  # type: ignore[assignment]
        before_eff = _compute_effective_months_for_aggregate(
            worker.joined_at,  # type: ignore[arg-type]
            before_start_ym,
            before_end_ym,
        )
        after_eff = _compute_effective_months_for_aggregate(
            worker.joined_at,  # type: ignore[arg-type]
            after_start_ym,
            after_end_ym,
        )
        worker_before = before_counts_map.get(wid, {})
        worker_after = after_counts_map.get(wid, {})

        (
            position_name,
            department_name,
            skill_rank_name,
            emp_type_name,
            is_non_default,
        ) = _resolve_worker_attributes(
            worker, position_map, department_map, skill_rank_map, employment_type_map
        )

        slot_stats = []
        for slot_type in SlotTypeEnum:
            slot_key = slot_type.value

            # Before
            before_slot = worker_before.get(slot_key, {})
            before_count = sum(before_slot.values())
            before_monthly_avg = before_count / before_eff

            # After
            after_slot = worker_after.get(slot_key, {})
            after_count = sum(after_slot.values())
            after_monthly_avg = after_count / after_eff

            delta_count = after_count - before_count
            threshold = outlier_thresholds.get(slot_key, 0.0)
            is_outlier = after_monthly_avg > threshold

            # weekday_stats は weekday_night のみ
            weekday_stats: list[ShiftVerifyWeekdayDelta] | None = None
            if slot_type == SlotTypeEnum.weekday_night:
                weekday_stats = [
                    ShiftVerifyWeekdayDelta(
                        weekday=wd,
                        before_count=before_slot.get(wd, 0),
                        before_monthly_avg=before_slot.get(wd, 0) / before_eff,
                        after_count=after_slot.get(wd, 0),
                        after_monthly_avg=after_slot.get(wd, 0) / after_eff,
                        delta_count=after_slot.get(wd, 0) - before_slot.get(wd, 0),
                    )
                    for wd in range(4)  # 0=月, 1=火, 2=水, 3=木
                ]

            slot_stats.append(
                ShiftVerifySlotStat(
                    slot_type=slot_type,
                    before_count=before_count,
                    before_monthly_avg=before_monthly_avg,
                    after_count=after_count,
                    after_monthly_avg=after_monthly_avg,
                    delta_count=delta_count,
                    is_outlier=is_outlier,
                    weekday_stats=weekday_stats,
                )
            )

        items.append(
            ShiftVerifyWorkerItem(
                worker_id=wid,
                worker_name=str(worker.name),
                position_name=position_name,
                department_name=department_name,
                skill_rank_name=skill_rank_name,
                employment_type_name=emp_type_name,
                is_non_default_employment=is_non_default,
                effective_months=after_eff,
                slot_stats=slot_stats,
            )
        )

    return ShiftVerifyResponse(
        year_month=year_month,
        before_period=before_period_str,
        after_period=after_period_str,
        items=items,
    )
