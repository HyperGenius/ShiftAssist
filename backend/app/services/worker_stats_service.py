# backend/app/services/worker_stats_service.py
"""ワーカー勤務実績統計集計サービス層.

``published`` 状態のシフトプランに基づき、ワーカーごとの枠種別勤務回数と
在籍期間を考慮した月平均値を集計・提供する。
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.models.models import (
    Department,
    EmploymentType,
    PlanStatusEnum,
    Position,
    ShiftAssignment,
    ShiftPlan,
    ShiftSlot,
    SlotTypeEnum,
    TenantSkillRank,
    TenantStatsConfig,
    Worker,
    WorkerMonthlySlotStats,
)
from app.models.schemas import (
    AggregateStatsResponse,
    AggregateWorkerSlotStats,
    AggregateWorkerStats,
    RecalculateStatsResponse,
    TenantStatsConfigResponse,
    TenantWorkerStatsResponse,
    WeekdayNightStats,
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
        config.stats_period_months = stats_period_months  # type: ignore[assignment]
        config.updated_at = datetime.now(UTC)  # type: ignore[assignment]

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
        worker_id=worker.id,  # type: ignore[arg-type]
        worker_name=worker.name,  # type: ignore[arg-type]
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
        worker.joined_at,  # type: ignore[arg-type]
        stats_period_months,
        today,
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
        count_by_slot = counts_map.get(worker.id, {})  # type: ignore[call-overload]
        effective_months = _compute_effective_months(
            worker.joined_at,  # type: ignore[arg-type]
            stats_period_months,
            today,
        )
        items.append(_build_stats_response(worker, count_by_slot, effective_months))

    return TenantWorkerStatsResponse(
        stats_period_months=stats_period_months,
        items=items,
    )


# ---------------------------------------------------------------------------
# 集計テーブル（WorkerMonthlySlotStats）操作
# ---------------------------------------------------------------------------

_AGGREGATE_PERIOD_MONTHS = 12


def _compute_aggregate_cutoff(year_month: str) -> tuple[str, str]:
    """選択年月を末月として直近12ヶ月の開始年月と終了年月を返す.

    例: year_month="2026-04" → start="2025-05", end="2026-04"

    Args:
        year_month: 選択年月（YYYY-MM形式）。

    Returns:
        (start_ym, end_ym) のタプル。
    """
    y, m = int(year_month[:4]), int(year_month[5:7])
    start_m = m - _AGGREGATE_PERIOD_MONTHS + 1
    start_y = y
    if start_m <= 0:
        start_m += 12
        start_y -= 1
    return f"{start_y:04d}-{start_m:02d}", year_month


def _compute_effective_months_for_aggregate(
    joined_at: date | None,
    start_ym: str,
    end_ym: str,
) -> float:
    """集計期間に対するワーカーの有効在籍月数を計算する.

    ``joined_at`` が集計期間内にある場合は途中参加として月数を短縮する。
    ``joined_at`` が集計期間より前または NULL の場合は12ヶ月を使用する。

    Args:
        joined_at: ワーカーの着任日。Noneの場合は12ヶ月全体を使用。
        start_ym: 集計開始年月（YYYY-MM形式）。
        end_ym: 集計終了年月（YYYY-MM形式）。

    Returns:
        有効在籍月数（最低値 1.0）。
    """
    if joined_at is None:
        return float(_AGGREGATE_PERIOD_MONTHS)

    # joined_at が集計期間より前なら全期間を使用
    joined_ym = f"{joined_at.year:04d}-{joined_at.month:02d}"
    if joined_ym <= start_ym:
        return float(_AGGREGATE_PERIOD_MONTHS)

    # joined_at が集計終了月より後なら最低値
    if joined_ym > end_ym:
        return 1.0

    # joined_at 月 〜 end_ym の月数を計算
    sy, sm = int(joined_ym[:4]), int(joined_ym[5:7])
    ey, em = int(end_ym[:4]), int(end_ym[5:7])
    months = (ey - sy) * 12 + (em - sm) + 1
    return max(float(months), 1.0)


def upsert_monthly_slot_stats(
    session: Session,
    tenant_id: str,
    year_month: str,
) -> bool:
    """指定年月の集計テーブルを Upsert する.

    ``published`` ステータスのシフトプランを参照して
    Worker × SlotType × weekday（weekday_nightのみ）ごとにシフト回数を集計し、
    ``worker_monthly_slot_stats`` テーブルへ Upsert する。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        year_month: 集計対象年月（YYYY-MM形式）。

    Returns:
        Upsert を実行した場合は ``True``、published プランが存在しない場合は ``False``。
    """
    # 対象プランを取得
    plan = session.exec(
        select(ShiftPlan).where(
            ShiftPlan.tenant_id == tenant_id,
            ShiftPlan.target_year_month == year_month,
            ShiftPlan.status == PlanStatusEnum.published,
        )
    ).first()

    if plan is None:
        return False

    now = datetime.now(UTC)
    upsert_values = []

    # --- 1. weekday_night 以外: 曜日不問で集計 (weekday=NULL) ---
    non_weekday_rows = session.exec(
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

    for row in non_weekday_rows:
        upsert_values.append(
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "worker_id": row[0],
                "year_month": year_month,
                "slot_type": str(row[1]),
                "weekday": None,
                "count": row[2],
                "updated_at": now,
            }
        )

    # --- 2. weekday_night: isodow 単位で集計し、月〜木は 0〜3 に、金〜日は NULL に変換 ---
    wn_rows = session.exec(
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

    # weekday_night を Python 側で worker × weekday_bucket に集約する
    wn_map: dict[tuple[uuid.UUID, int | None], int] = {}
    for row in wn_rows:
        worker_id: uuid.UUID = row[0]
        isodow = int(row[1]) if row[1] is not None else None
        cnt = int(row[2])
        # isodow 1〜4 → weekday 0〜3 (月〜木), 5〜7 → None
        weekday: int | None = (
            (isodow - 1) if (isodow is not None and 1 <= isodow <= 4) else None
        )
        key = (worker_id, weekday)
        wn_map[key] = wn_map.get(key, 0) + cnt

    for (worker_id, weekday), cnt in wn_map.items():
        upsert_values.append(
            {
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "worker_id": worker_id,
                "year_month": year_month,
                "slot_type": SlotTypeEnum.weekday_night.value,
                "weekday": weekday,
                "count": cnt,
                "updated_at": now,
            }
        )

    if not upsert_values:
        return (
            True  # プランは存在するがアサインメントがない場合もupsert実行済みとみなす
        )

    # ON CONFLICT DO UPDATE (Upsert)
    stmt = pg_insert(WorkerMonthlySlotStats).values(upsert_values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_worker_monthly_slot_stats",
        set_={
            "count": stmt.excluded.count,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.exec(stmt)  # type: ignore[arg-type]
    session.commit()
    return True


def _build_slot_stats(
    worker_counts: dict[str, dict[int | None, int]],
    effective_months: float,
) -> list[AggregateWorkerSlotStats]:
    """SlotTypeEnum ごとの集計統計リストを構築するヘルパー."""
    slot_stats = []
    for slot_type in SlotTypeEnum:
        slot_counts = worker_counts.get(slot_type.value, {})
        total_count = sum(slot_counts.values())
        monthly_avg = total_count / effective_months

        weekday_stats: list[WeekdayNightStats] | None = None
        if slot_type == SlotTypeEnum.weekday_night:
            weekday_stats = [
                WeekdayNightStats(
                    weekday=wd,
                    count=slot_counts.get(wd, 0),
                    monthly_avg=slot_counts.get(wd, 0) / effective_months,
                )
                for wd in range(4)  # 0=月, 1=火, 2=水, 3=木
            ]

        slot_stats.append(
            AggregateWorkerSlotStats(
                slot_type=slot_type,
                count=total_count,
                monthly_avg=monthly_avg,
                weekday_stats=weekday_stats,
            )
        )
    return slot_stats


def _resolve_worker_attributes(
    worker: Worker,
    position_map: dict[uuid.UUID, str],
    department_map: dict[uuid.UUID, str],
    skill_rank_map: dict[uuid.UUID, str],
    employment_type_map: dict[uuid.UUID, tuple[str, bool]],
) -> tuple[str | None, str | None, str | None, str | None, bool]:
    """Worker の FK から関連属性名と非デフォルト雇用形態フラグを解決するヘルパー.

    Returns:
        (position_name, department_name, skill_rank_name, emp_type_name, is_non_default)
    """
    position_name = position_map.get(worker.position_id) if worker.position_id else None  # type: ignore[call-overload]
    department_name = (
        department_map.get(worker.department_id) if worker.department_id else None  # type: ignore[call-overload]
    )
    skill_rank_name = (
        skill_rank_map.get(worker.skill_rank_id) if worker.skill_rank_id else None  # type: ignore[call-overload]
    )

    emp_type_name: str | None = None
    is_non_default = bool(worker.is_special)
    if worker.employment_type_id:
        et = employment_type_map.get(worker.employment_type_id)  # type: ignore[call-overload]
        if et is not None:
            emp_type_name, is_default = et
            if not is_default:
                is_non_default = True

    return (
        position_name,
        department_name,
        skill_rank_name,
        emp_type_name,
        is_non_default,
    )


def get_aggregate_stats(
    session: Session,
    tenant_id: str,
    year_month: str,
) -> AggregateStatsResponse:
    """選択年月を末月とした直近12ヶ月の集計情報を返す.

    ``WorkerMonthlySlotStats`` テーブルを参照して Worker 別・SlotType 別の
    合計を集計し、``joined_at`` による有効月数正規化を適用して月平均を算出する。
    N+1 問題回避のため、関連テーブル（Position / Department / TenantSkillRank /
    EmploymentType）はバッチクエリで一括取得する。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        year_month: 選択年月（YYYY-MM形式）。省略時は当月。

    Returns:
        AggregateStatsResponse。
    """
    start_ym, end_ym = _compute_aggregate_cutoff(year_month)

    workers = session.exec(select(Worker).where(Worker.tenant_id == tenant_id)).all()

    if not workers:
        return AggregateStatsResponse(
            year_month=year_month,
            period_months=_AGGREGATE_PERIOD_MONTHS,
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

    # 集計テーブルから直近12ヶ月分のデータを取得
    stats_rows = session.exec(
        select(
            WorkerMonthlySlotStats.worker_id,
            WorkerMonthlySlotStats.slot_type,
            WorkerMonthlySlotStats.weekday,
            func.sum(WorkerMonthlySlotStats.count).label("total"),
        )
        .where(
            WorkerMonthlySlotStats.tenant_id == tenant_id,
            WorkerMonthlySlotStats.worker_id.in_(worker_ids),  # type: ignore[union-attr]
            WorkerMonthlySlotStats.year_month >= start_ym,
            WorkerMonthlySlotStats.year_month <= end_ym,
        )
        .group_by(
            WorkerMonthlySlotStats.worker_id,
            WorkerMonthlySlotStats.slot_type,
            WorkerMonthlySlotStats.weekday,
        )
    ).all()

    # worker_id → slot_type → weekday → count のネストマップを構築
    counts_map: dict[uuid.UUID, dict[str, dict[int | None, int]]] = {}
    for row in stats_rows:
        wid: uuid.UUID = row[0]
        slot_type = str(row[1])
        weekday: int | None = row[2]
        total = int(row[3])
        if wid not in counts_map:
            counts_map[wid] = {}
        if slot_type not in counts_map[wid]:
            counts_map[wid][slot_type] = {}
        counts_map[wid][slot_type][weekday] = total

    items = []
    for worker in workers:
        effective_months = _compute_effective_months_for_aggregate(
            worker.joined_at,  # type: ignore[arg-type]
            start_ym,
            end_ym,
        )
        worker_counts = counts_map.get(worker.id, {})  # type: ignore[call-overload]

        (
            position_name,
            department_name,
            skill_rank_name,
            emp_type_name,
            is_non_default,
        ) = _resolve_worker_attributes(
            worker, position_map, department_map, skill_rank_map, employment_type_map
        )

        slot_stats = _build_slot_stats(worker_counts, effective_months)

        items.append(
            AggregateWorkerStats(
                worker_id=worker.id,  # type: ignore[arg-type]
                worker_name=worker.name,  # type: ignore[arg-type]
                effective_months=effective_months,
                slot_stats=slot_stats,
                position_name=position_name,
                department_name=department_name,
                skill_rank_name=skill_rank_name,
                employment_type_name=emp_type_name,
                is_non_default_employment=is_non_default,
                joined_at=worker.joined_at,  # type: ignore[arg-type]
                skill_acquired_at=worker.skill_acquired_at,  # type: ignore[arg-type]
            )
        )

    return AggregateStatsResponse(
        year_month=year_month,
        period_months=_AGGREGATE_PERIOD_MONTHS,
        items=items,
    )


# ---------------------------------------------------------------------------
# 再計算エンドポイント用レートリミット
# ---------------------------------------------------------------------------

# テナントIDごとの最終再計算日時を保持するインメモリキャッシュ。
# 注意: このキャッシュはプロセス内メモリのみで管理するため、
#       複数プロセス・複数インスタンスで稼働する場合はプロセスをまたいだ
#       クールダウンが機能しない。現状はシングルインスタンス運用を前提とする。
_recalculate_last_called: dict[str, datetime] = {}
_RECALCULATE_COOLDOWN_SECONDS = 60


def check_and_update_recalculate_cooldown(tenant_id: str) -> bool:
    """再計算クールダウンを確認し、実行可能なら記録を更新する.

    実行可能な場合は内部状態を更新して ``True`` を返す。
    クールダウン中の場合は ``False`` を返す。

    Args:
        tenant_id: テナントID。

    Returns:
        実行可能なら ``True``、クールダウン中なら ``False``。
    """
    now = datetime.now(UTC)
    last = _recalculate_last_called.get(tenant_id)
    if last is not None:
        elapsed = (now - last).total_seconds()
        if elapsed < _RECALCULATE_COOLDOWN_SECONDS:
            return False
    _recalculate_last_called[tenant_id] = now
    return True


def recalculate_all_stats(
    session: Session,
    tenant_id: str,
    year_month: str,
) -> RecalculateStatsResponse:
    """選択年月を末月とした直近12ヶ月の集計テーブルを全月一括再計算する.

    ``published`` ステータスのシフトプランが存在する月のみ Upsert を実行し、
    実際に Upsert した年月のリストを返す。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        year_month: 集計末月（YYYY-MM形式）。

    Returns:
        RecalculateStatsResponse（published プランが存在しUpsertを実行した年月リスト）。
    """
    start_ym, end_ym = _compute_aggregate_cutoff(year_month)

    # 集計対象の年月リストを生成
    target_months: list[str] = []
    y, m = int(start_ym[:4]), int(start_ym[5:7])
    ey, em = int(end_ym[:4]), int(end_ym[5:7])
    while (y, m) <= (ey, em):
        target_months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1

    # published プランが存在した月のみ upserted リストに追加する
    upserted: list[str] = []
    for ym in target_months:
        if upsert_monthly_slot_stats(session, tenant_id, ym):
            upserted.append(ym)

    return RecalculateStatsResponse(
        year_month=year_month,
        upserted_months=upserted,
    )
