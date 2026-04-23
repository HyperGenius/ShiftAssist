# backend/tests/unit/test_shift_verify_service.py
"""shift_verify_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from app.models.models import (
    PlanStatusEnum,
    ShiftPlan,
    SlotTypeEnum,
    Worker,
)
from app.models.schemas import (
    ShiftVerifyResponse,
    ShiftVerifyWorkerItem,
)
from app.services import shift_verify_service

# ---------------------------------------------------------------------------
# テスト用定数
# ---------------------------------------------------------------------------

TENANT_ID = "org_verify_test"
PLAN_ID = uuid.uuid4()
WORKER_ID_1 = uuid.uuid4()
WORKER_ID_2 = uuid.uuid4()
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
    w.id = worker_id or WORKER_ID_1
    w.tenant_id = TENANT_ID
    w.name = name
    w.department_id = DEPT_ID
    w.skill_rank_id = SKILL_RANK_ID
    w.is_special = False
    w.joined_at = joined_at
    w.position_id = None
    w.employment_type_id = None
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


def _make_plan(
    *,
    plan_id: uuid.UUID | None = None,
    target_year_month: str = "2026-06",
    status: PlanStatusEnum = PlanStatusEnum.published,
) -> ShiftPlan:
    """テスト用ShiftPlanオブジェクトを生成するヘルパー."""
    p = ShiftPlan()
    p.id = plan_id or PLAN_ID
    p.tenant_id = TENANT_ID
    p.title = f"シフト {target_year_month}"
    p.target_year_month = target_year_month
    p.status = status
    p.created_by = "test_user"
    p.created_at = datetime(2026, 1, 1)
    return p


def _make_session_with_sequence(responses: list[object]) -> MagicMock:
    """exec 呼び出しのたびに responses から順に first/all を返す Session モック."""
    session = MagicMock()
    call_index = [0]

    def exec_side_effect(query: object) -> MagicMock:
        result = MagicMock()
        idx = call_index[0]
        call_index[0] += 1
        resp = responses[idx] if idx < len(responses) else []
        if isinstance(resp, Sequence) and not isinstance(resp, (str, bytes)):
            result.all.return_value = list(resp)
            result.first.return_value = resp[0] if resp else None
        else:
            result.first.return_value = resp
            result.all.return_value = [resp] if resp is not None else []
        return result

    session.exec.side_effect = exec_side_effect
    return session


# ---------------------------------------------------------------------------
# _prev_month_ym
# ---------------------------------------------------------------------------


class TestPrevMonthYm:
    """_prev_month_ym の正常系テスト."""

    def test_mid_year(self) -> None:
        """通常の月（6月）→ 5月。"""
        assert shift_verify_service._prev_month_ym("2026-06") == "2026-05"

    def test_january_wraps_to_december(self) -> None:
        """1月 → 前年12月。"""
        assert shift_verify_service._prev_month_ym("2026-01") == "2025-12"

    def test_december(self) -> None:
        """12月 → 11月。"""
        assert shift_verify_service._prev_month_ym("2026-12") == "2026-11"

    def test_february(self) -> None:
        """2月 → 1月。"""
        assert shift_verify_service._prev_month_ym("2026-02") == "2026-01"


# ---------------------------------------------------------------------------
# Before/After 期間の計算
# ---------------------------------------------------------------------------


class TestBeforeAfterPeriod:
    """Before/After 期間算出ロジックのテスト."""

    def test_period_strings_for_june_2026(self) -> None:
        """2026-06 のシフトプランで Before/After 期間が要件通り。

        Before: 2025-06 〜 2026-05
        After:  2025-07 〜 2026-06
        """
        before_end = shift_verify_service._prev_month_ym("2026-06")
        assert before_end == "2026-05"

        from app.services.worker_stats_service import _compute_aggregate_cutoff

        before_start, _ = _compute_aggregate_cutoff(before_end)
        assert before_start == "2025-06"

        after_start, after_end = _compute_aggregate_cutoff("2026-06")
        assert after_start == "2025-07"
        assert after_end == "2026-06"

    def test_period_strings_for_january_2026(self) -> None:
        """2026-01 のシフトプランで年をまたぐ期間が正しい。

        Before: 2024-02 〜 2025-12
        After:  2025-01 〜 2026-01
        """
        before_end = shift_verify_service._prev_month_ym("2026-01")
        assert before_end == "2025-12"

        from app.services.worker_stats_service import _compute_aggregate_cutoff

        before_start, _ = _compute_aggregate_cutoff(before_end)
        assert before_start == "2025-01"

        after_start, after_end = _compute_aggregate_cutoff("2026-01")
        assert after_start == "2025-02"
        assert after_end == "2026-01"


# ---------------------------------------------------------------------------
# get_shift_verify_stats
# ---------------------------------------------------------------------------


class TestGetShiftVerifyStats:
    """get_shift_verify_stats の正常系・異常系テスト."""

    def test_returns_404_when_plan_not_found(self) -> None:
        """存在しないプランIDで 404 が発生する。"""
        from fastapi import HTTPException

        session = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = None
        session.exec.return_value = exec_result

        with pytest.raises(HTTPException) as exc_info:
            shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert exc_info.value.status_code == 404

    def test_returns_empty_items_when_no_workers(self) -> None:
        """ワーカーが存在しない場合、空の items を返す。"""
        plan = _make_plan(target_year_month="2026-06")

        # exec 呼び出し順:
        # 0: ShiftPlan.first() → plan
        # 1: Worker.all() → []
        session = _make_session_with_sequence([plan, []])

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert isinstance(result, ShiftVerifyResponse)
        assert result.year_month == "2026-06"
        assert result.before_period == "2025-06 〜 2026-05"
        assert result.after_period == "2025-07 〜 2026-06"
        assert result.items == []

    def test_returns_correct_periods(self) -> None:
        """year_month = 2026-06 のとき Before/After 期間が要件通り。"""
        plan = _make_plan(target_year_month="2026-06")

        session = _make_session_with_sequence([plan, []])

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert result.before_period == "2025-06 〜 2026-05"
        assert result.after_period == "2025-07 〜 2026-06"

    def test_returns_period_crossing_year(self) -> None:
        """year_month = 2026-01 のとき年をまたぐ期間が正しい。"""
        plan = _make_plan(target_year_month="2026-01")

        session = _make_session_with_sequence([plan, []])

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert result.before_period == "2025-01 〜 2025-12"
        assert result.after_period == "2025-02 〜 2026-01"

    def test_worker_without_before_stats_shows_zero_before(self) -> None:
        """Before 集計が存在しない新規 Worker でもエラーにならず before_count=0 で返る。"""
        plan = _make_plan(target_year_month="2026-06")
        # 入社したばかりのワーカー
        worker = _make_worker(joined_at=date(2026, 6, 1))

        # exec 呼び出し順:
        # 0: ShiftPlan.first()
        # 1: Worker.all()
        # 2: Position.all() → []
        # 3: Department.all() → []
        # 4: TenantSkillRank.all() → []
        # 5: EmploymentType.all() → []
        # 6: Before stats (WorkerMonthlySlotStats) → []（Before なし）
        # 7: After base stats → []
        # 8: non-weekday_night plan assignments → []
        # 9: weekday_night plan assignments → []
        responses: list[object] = [
            plan,
            [worker],
            [],  # Position
            [],  # Department
            [],  # TenantSkillRank
            [],  # EmploymentType
            [],  # Before stats
            [],  # After base stats
            [],  # non-wn plan assignments
            [],  # wn plan assignments
        ]
        session = _make_session_with_sequence(responses)

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert len(result.items) == 1
        item: ShiftVerifyWorkerItem = result.items[0]
        # Before カウントはすべて 0
        for stat in item.slot_stats:
            assert stat.before_count == 0

    def test_after_count_includes_plan_assignments(self) -> None:
        """ShiftPlan のアサインメントが After カウントに加算される。"""
        plan = _make_plan(target_year_month="2026-06")
        worker = _make_worker()

        # ShiftPlan の non-weekday_night assignments のシミュレーション
        # (worker_id, slot_type, cnt) のタプルリスト
        plan_assignments = [
            (WORKER_ID_1, SlotTypeEnum.sat_day, 2),
        ]

        responses: list[object] = [
            plan,
            [worker],
            [],  # Position
            [],  # Department
            [],  # TenantSkillRank
            [],  # EmploymentType
            [],  # Before stats (worker_monthly_slot_stats before)
            [],  # After base stats (worker_monthly_slot_stats after_start..before_end)
            plan_assignments,  # non-wn plan assignments
            [],  # wn plan assignments
        ]
        session = _make_session_with_sequence(responses)

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert len(result.items) == 1
        item = result.items[0]
        sat_day_stat = next(s for s in item.slot_stats if s.slot_type == SlotTypeEnum.sat_day)
        assert sat_day_stat.after_count == 2
        assert sat_day_stat.before_count == 0
        assert sat_day_stat.delta_count == 2

    def test_is_outlier_true_for_high_avg(self) -> None:
        """After 月平均が他の Worker より大幅に高い場合 is_outlier=True になる。"""
        plan = _make_plan(target_year_month="2026-06")
        worker1 = _make_worker(worker_id=WORKER_ID_1, name="高アサインワーカー")
        worker2 = _make_worker(worker_id=WORKER_ID_2, name="低アサインワーカー1")
        worker3_id = uuid.uuid4()
        worker3 = _make_worker(worker_id=worker3_id, name="低アサインワーカー2")

        # worker1 に sat_day で大量アサイン（30回）、worker2/3 は 0
        # after_eff = 12, worker1 avg = 30/12 = 2.5
        # mean = 2.5/3 ≈ 0.833
        # std ≈ sqrt(((2.5-0.833)^2 + (0-0.833)^2 * 2) / 3) ≈ 1.18
        # threshold ≈ 2.01 → worker1 avg 2.5 > 2.01 → is_outlier = True
        plan_assignments_w1 = [
            (WORKER_ID_1, SlotTypeEnum.sat_day, 30),
        ]

        responses: list[object] = [
            plan,
            [worker1, worker2, worker3],
            [],  # Position
            [],  # Department
            [],  # TenantSkillRank
            [],  # EmploymentType
            [],  # Before stats
            [],  # After base stats
            plan_assignments_w1,  # non-wn plan assignments
            [],  # wn plan assignments
        ]
        session = _make_session_with_sequence(responses)

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        assert len(result.items) == 3
        item1 = next(i for i in result.items if i.worker_id == WORKER_ID_1)
        item2 = next(i for i in result.items if i.worker_id == WORKER_ID_2)

        sat_day_1 = next(s for s in item1.slot_stats if s.slot_type == SlotTypeEnum.sat_day)
        sat_day_2 = next(s for s in item2.slot_stats if s.slot_type == SlotTypeEnum.sat_day)

        assert sat_day_1.is_outlier is True
        assert sat_day_2.is_outlier is False

    def test_weekday_stats_present_for_weekday_night(self) -> None:
        """weekday_night 枠に weekday_stats が含まれる。"""
        plan = _make_plan(target_year_month="2026-06")
        worker = _make_worker()

        responses: list[object] = [
            plan,
            [worker],
            [],  # Position
            [],  # Department
            [],  # TenantSkillRank
            [],  # EmploymentType
            [],  # Before stats
            [],  # After base stats
            [],  # non-wn plan assignments
            [],  # wn plan assignments
        ]
        session = _make_session_with_sequence(responses)

        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)

        item = result.items[0]
        wn_stat = next(s for s in item.slot_stats if s.slot_type == SlotTypeEnum.weekday_night)
        assert wn_stat.weekday_stats is not None
        assert len(wn_stat.weekday_stats) == 4
        weekdays = [ws.weekday for ws in wn_stat.weekday_stats]
        assert weekdays == [0, 1, 2, 3]

    def test_draft_plan_is_also_verifiable(self) -> None:
        """published でない（draft）プランでも Verify が実行できる。"""
        plan = _make_plan(target_year_month="2026-06", status=PlanStatusEnum.draft)

        responses: list[object] = [plan, []]
        session = _make_session_with_sequence(responses)

        # 404 が発生しないことを確認
        result = shift_verify_service.get_shift_verify_stats(session, TENANT_ID, PLAN_ID)
        assert isinstance(result, ShiftVerifyResponse)
