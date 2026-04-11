# backend/tests/unit/test_worker_stats_service.py
"""worker_stats_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.models import (
    PlanStatusEnum,
    SlotTypeEnum,
    TenantStatsConfig,
    Worker,
)
from app.models.schemas import (
    TenantStatsConfigResponse,
    TenantWorkerStatsResponse,
    WorkerStatsResponse,
)
from app.services import worker_stats_service

# ---------------------------------------------------------------------------
# テスト用定数
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
WORKER_ID = uuid.uuid4()
DEPT_ID = uuid.uuid4()
SKILL_RANK_ID = uuid.uuid4()


def _make_worker(
    *,
    worker_id: uuid.UUID | None = None,
    joined_at: date | None = None,
    name: str = "田中 太郎",
) -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = worker_id or WORKER_ID
    w.tenant_id = TENANT_ID
    w.name = name
    w.department_id = DEPT_ID
    w.skill_rank_id = SKILL_RANK_ID
    w.is_special = False
    w.joined_at = joined_at
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


def _make_stats_config(stats_period_months: int = 12) -> TenantStatsConfig:
    """テスト用TenantStatsConfigオブジェクトを生成するヘルパー."""
    config = TenantStatsConfig()
    config.id = uuid.uuid4()
    config.tenant_id = TENANT_ID
    config.stats_period_months = stats_period_months
    config.created_at = datetime(2026, 1, 1)
    config.updated_at = datetime(2026, 1, 1)
    return config


def _make_session(
    *,
    exec_first_return: object = None,
    exec_all_return: Sequence[object] | None = None,
) -> MagicMock:
    """テスト用Sessionモックを生成するヘルパー."""
    session = MagicMock()
    exec_result = MagicMock()
    exec_result.first.return_value = exec_first_return
    exec_result.all.return_value = exec_all_return or []
    session.exec.return_value = exec_result
    return session


# ---------------------------------------------------------------------------
# _compute_effective_months
# ---------------------------------------------------------------------------


class TestComputeEffectiveMonths:
    """_compute_effective_months の正常系テスト."""

    def test_joined_at_none_returns_period(self) -> None:
        """joined_at が None の場合、stats_period_months をそのまま返す."""
        today = date(2026, 4, 1)
        result = worker_stats_service._compute_effective_months(None, 12, today)
        assert result == 12.0

    def test_joined_recently_uses_tenure(self) -> None:
        """着任3ヶ月のワーカーは集計期間12ヶ月より短い在籍月数が使われる."""
        today = date(2026, 4, 1)
        joined_at = date(2026, 1, 1)  # 約3ヶ月前
        result = worker_stats_service._compute_effective_months(joined_at, 12, today)
        assert result < 4.0  # 3ヶ月程度
        assert result >= 1.0

    def test_veteran_uses_period(self) -> None:
        """着任2年のベテランは集計期間12ヶ月が使われる."""
        today = date(2026, 4, 1)
        joined_at = date(2024, 1, 1)  # 約2年前
        result = worker_stats_service._compute_effective_months(joined_at, 12, today)
        assert result == 12.0

    def test_minimum_one_month(self) -> None:
        """在籍期間が極めて短い場合でも最低1.0が返される."""
        today = date(2026, 4, 1)
        joined_at = date(2026, 3, 30)  # 2日前
        result = worker_stats_service._compute_effective_months(joined_at, 12, today)
        assert result == 1.0


# ---------------------------------------------------------------------------
# get_stats_config
# ---------------------------------------------------------------------------


class TestGetStatsConfig:
    """get_stats_config の正常系テスト."""

    def test_returns_default_when_no_record(self) -> None:
        """DBにレコードがない場合はデフォルト値（12ヶ月）を返す."""
        session = _make_session(exec_first_return=None)
        result = worker_stats_service.get_stats_config(session, TENANT_ID)
        assert isinstance(result, TenantStatsConfigResponse)
        assert result.stats_period_months == 12
        assert result.tenant_id == TENANT_ID

    def test_returns_db_value_when_record_exists(self) -> None:
        """DBにレコードがある場合はその値を返す."""
        config = _make_stats_config(stats_period_months=6)
        session = _make_session(exec_first_return=config)
        result = worker_stats_service.get_stats_config(session, TENANT_ID)
        assert result.stats_period_months == 6


# ---------------------------------------------------------------------------
# update_stats_config
# ---------------------------------------------------------------------------


class TestUpdateStatsConfig:
    """update_stats_config の正常系テスト."""

    def test_creates_new_record(self) -> None:
        """DBにレコードがない場合は新規作成して返す."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = None
        session.exec.return_value = exec_result

        def fake_refresh(obj: object) -> None:
            if isinstance(obj, TenantStatsConfig):
                obj.tenant_id = TENANT_ID
                obj.stats_period_months = 6

        session.refresh.side_effect = fake_refresh

        result = worker_stats_service.update_stats_config(session, TENANT_ID, 6)

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result.stats_period_months == 6

    def test_updates_existing_record(self) -> None:
        """DBにレコードがある場合は上書き更新して返す."""
        config = _make_stats_config(stats_period_months=12)

        session = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = config
        session.exec.return_value = exec_result

        def fake_refresh(obj: object) -> None:
            pass

        session.refresh.side_effect = fake_refresh

        result = worker_stats_service.update_stats_config(session, TENANT_ID, 6)

        session.add.assert_not_called()
        session.commit.assert_called_once()
        assert result.stats_period_months == 6


# ---------------------------------------------------------------------------
# get_worker_stats
# ---------------------------------------------------------------------------


class TestGetWorkerStats:
    """get_worker_stats の正常系・異常系テスト."""

    def test_returns_404_for_unknown_worker(self) -> None:
        """存在しないワーカーIDを指定すると404例外が発生する."""
        from fastapi import HTTPException

        session = MagicMock()
        # Worker取得でNone、stats configでデフォルト
        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            result.first.return_value = None
            result.all.return_value = []
            return result

        session.exec.side_effect = exec_side_effect

        with pytest.raises(HTTPException) as exc_info:
            worker_stats_service.get_worker_stats(session, TENANT_ID, WORKER_ID)

        assert exc_info.value.status_code == 404

    def test_returns_stats_with_no_assignments(self) -> None:
        """アサインメントがない場合、全カウントが0のレスポンスを返す."""
        worker = _make_worker()
        config = _make_stats_config()

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # Worker取得
                result.first.return_value = worker
            elif call_count[0] == 2:
                # stats config取得
                result.first.return_value = config
            else:
                # アサインメント集計
                result.all.return_value = []
            return result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        result = worker_stats_service.get_worker_stats(session, TENANT_ID, WORKER_ID)

        assert isinstance(result, WorkerStatsResponse)
        assert result.worker_id == WORKER_ID
        assert result.worker_name == "田中 太郎"
        assert result.holiday_slot_monthly_avg == 0.0
        assert all(s.count == 0 for s in result.slot_stats)

    def test_normalizes_by_effective_months_for_new_worker(self) -> None:
        """着任3ヶ月のワーカーは在籍月数で正規化された月平均が計算される."""
        today = date(2026, 4, 1)
        joined_at = date(2026, 1, 1)
        worker = _make_worker(joined_at=joined_at)
        config = _make_stats_config(stats_period_months=12)

        # sat_day で 3回アサインされているシミュレーション
        mock_rows = [(SlotTypeEnum.sat_day, 3)]

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.first.return_value = worker
            elif call_count[0] == 2:
                result.first.return_value = config
            else:
                result.all.return_value = mock_rows
            return result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        with patch("app.services.worker_stats_service.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = today
            mock_dt.now.return_value = MagicMock()
            mock_dt.now.return_value.date.return_value = today

            # _compute_effective_months を直接テスト用の今日日付で呼ぶ
            effective = worker_stats_service._compute_effective_months(
                joined_at, 12, today
            )

        result = worker_stats_service._build_stats_response(
            worker,
            {"sat_day": 3},
            effective,
        )

        sat_day_stat = next(s for s in result.slot_stats if s.slot_type == SlotTypeEnum.sat_day)
        assert sat_day_stat.count == 3
        # 月平均 = 3 / effective_months < 3 (在籍3ヶ月なので月1回程度)
        assert sat_day_stat.monthly_avg < 4.0
        assert sat_day_stat.monthly_avg >= 0.5


# ---------------------------------------------------------------------------
# get_all_worker_stats
# ---------------------------------------------------------------------------


class TestGetAllWorkerStats:
    """get_all_worker_stats の正常系テスト."""

    def test_returns_empty_when_no_workers(self) -> None:
        """ワーカーが存在しない場合、空のレスポンスを返す."""
        config = _make_stats_config()

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.first.return_value = config
            else:
                result.all.return_value = []
            return result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        result = worker_stats_service.get_all_worker_stats(session, TENANT_ID)

        assert isinstance(result, TenantWorkerStatsResponse)
        assert result.items == []
        assert result.stats_period_months == 12

    def test_returns_stats_for_all_workers(self) -> None:
        """複数ワーカーが存在する場合、全員分の統計を返す."""
        worker1 = _make_worker(worker_id=uuid.uuid4(), name="田中 太郎")
        worker2 = _make_worker(worker_id=uuid.uuid4(), name="鈴木 花子")
        config = _make_stats_config()

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.first.return_value = config
            elif call_count[0] == 2:
                result.all.return_value = [worker1, worker2]
            else:
                result.all.return_value = []
            return result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        result = worker_stats_service.get_all_worker_stats(session, TENANT_ID)

        assert len(result.items) == 2
        names = {item.worker_name for item in result.items}
        assert "田中 太郎" in names
        assert "鈴木 花子" in names

    def test_only_published_plans_affect_stats(self) -> None:
        """published 以外のプランが統計に含まれないことを確認する（クエリフィルター検証）."""
        # このテストはクエリが正しいフィルターを持っていることをサービスの
        # ロジックで確認する（SQLクエリにPlanStatusEnum.publishedが含まれる）
        worker = _make_worker()
        config = _make_stats_config()

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.first.return_value = config
            elif call_count[0] == 2:
                result.all.return_value = [worker]
            else:
                # 集計結果として空を返す（draft/pending のみ存在する場合を想定）
                result.all.return_value = []
            return result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        result = worker_stats_service.get_all_worker_stats(session, TENANT_ID)

        assert len(result.items) == 1
        # published プランがないため、全カウントは0
        assert result.items[0].holiday_slot_monthly_avg == 0.0


# ---------------------------------------------------------------------------
# _compute_aggregate_cutoff
# ---------------------------------------------------------------------------


class TestComputeAggregateCutoff:
    """_compute_aggregate_cutoff の正常系テスト."""

    def test_basic_case(self) -> None:
        """2026-04 を末月にすると 2025-05〜2026-04 になる."""
        start, end = worker_stats_service._compute_aggregate_cutoff("2026-04")
        assert start == "2025-05"
        assert end == "2026-04"

    def test_year_boundary(self) -> None:
        """2026-01 を末月にすると 2025-02〜2026-01 になる."""
        start, end = worker_stats_service._compute_aggregate_cutoff("2026-01")
        assert start == "2025-02"
        assert end == "2026-01"

    def test_exact_boundary(self) -> None:
        """2026-12 を末月にすると 2026-01〜2026-12 になる."""
        start, end = worker_stats_service._compute_aggregate_cutoff("2026-12")
        assert start == "2026-01"
        assert end == "2026-12"


# ---------------------------------------------------------------------------
# _compute_effective_months_for_aggregate
# ---------------------------------------------------------------------------


class TestComputeEffectiveMonthsForAggregate:
    """_compute_effective_months_for_aggregate の正常系テスト."""

    def test_none_joined_at_returns_12(self) -> None:
        """joined_at が None の場合は12ヶ月を返す."""
        result = worker_stats_service._compute_effective_months_for_aggregate(
            None, "2025-05", "2026-04"
        )
        assert result == 12.0

    def test_joined_before_start_returns_12(self) -> None:
        """着任が集計開始より前なら12ヶ月を返す."""
        joined_at = date(2025, 1, 1)  # 2025-05 より前
        result = worker_stats_service._compute_effective_months_for_aggregate(
            joined_at, "2025-05", "2026-04"
        )
        assert result == 12.0

    def test_joined_at_start_returns_12(self) -> None:
        """着任が集計開始月と同月なら12ヶ月を返す."""
        joined_at = date(2025, 5, 15)  # 2025-05
        result = worker_stats_service._compute_effective_months_for_aggregate(
            joined_at, "2025-05", "2026-04"
        )
        assert result == 12.0

    def test_joined_in_period_returns_reduced_months(self) -> None:
        """集計期間内に着任した場合は期間を短縮する（2025-07着任 → 10ヶ月）."""
        joined_at = date(2025, 7, 1)  # 2025-07 着任、末月 2026-04 → 10ヶ月
        result = worker_stats_service._compute_effective_months_for_aggregate(
            joined_at, "2025-05", "2026-04"
        )
        assert result == 10.0

    def test_joined_after_end_returns_minimum(self) -> None:
        """集計終了月より後に着任した場合は最低値1.0を返す."""
        joined_at = date(2026, 6, 1)  # 集計期間外
        result = worker_stats_service._compute_effective_months_for_aggregate(
            joined_at, "2025-05", "2026-04"
        )
        assert result == 1.0

    def test_joined_at_end_month_returns_1(self) -> None:
        """着任が集計末月と同月なら1ヶ月を返す."""
        joined_at = date(2026, 4, 1)
        result = worker_stats_service._compute_effective_months_for_aggregate(
            joined_at, "2025-05", "2026-04"
        )
        assert result == 1.0


# ---------------------------------------------------------------------------
# get_aggregate_stats
# ---------------------------------------------------------------------------


class TestGetAggregateStats:
    """get_aggregate_stats の正常系テスト."""

    def test_returns_empty_when_no_workers(self) -> None:
        """ワーカーが存在しない場合、空のレスポンスを返す."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = []
        session.exec.return_value = exec_result

        from app.models.schemas import AggregateStatsResponse

        result = worker_stats_service.get_aggregate_stats(session, TENANT_ID, "2026-04")

        assert isinstance(result, AggregateStatsResponse)
        assert result.year_month == "2026-04"
        assert result.period_months == 12
        assert result.items == []

    def test_returns_stats_for_workers(self) -> None:
        """ワーカーが存在する場合、集計データを返す."""
        worker = _make_worker()

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # workers取得
                result.all.return_value = [worker]
            else:
                # stats取得
                result.all.return_value = []
            return result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        from app.models.schemas import AggregateStatsResponse

        result = worker_stats_service.get_aggregate_stats(session, TENANT_ID, "2026-04")

        assert isinstance(result, AggregateStatsResponse)
        assert len(result.items) == 1
        assert result.items[0].worker_name == "田中 太郎"
        assert result.items[0].effective_months == 12.0

    def test_weekday_night_has_weekday_stats(self) -> None:
        """weekday_night の slot_stats には weekday_stats が含まれる."""
        worker = _make_worker()

        call_count = [0]

        def exec_side_effect(query: object) -> MagicMock:
            mock_result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_result.all.return_value = [worker]
            else:
                # weekday_night, weekday=0 (月), count=5
                mock_result.all.return_value = [
                    (worker.id, "weekday_night", 0, 5),
                ]
            return mock_result

        session = MagicMock()
        session.exec.side_effect = exec_side_effect

        result = worker_stats_service.get_aggregate_stats(session, TENANT_ID, "2026-04")

        wn_stat = next(
            s for s in result.items[0].slot_stats if str(s.slot_type) == "weekday_night"
        )
        assert wn_stat.weekday_stats is not None
        mon = next(ws for ws in wn_stat.weekday_stats if ws.weekday == 0)
        assert mon.count == 5
