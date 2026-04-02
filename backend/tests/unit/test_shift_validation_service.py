# backend/tests/unit/test_shift_validation_service.py
"""shift_validation_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.models import ShiftRequirement, Worker
from app.models.rule_schemas import ShiftRulesConfig
from app.services import shift_validation_service

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
REQ_ID = uuid.uuid4()
DEPT_A_ID = uuid.uuid4()
DEPT_B_ID = uuid.uuid4()
WORKER_ID_1 = uuid.uuid4()
WORKER_ID_2 = uuid.uuid4()
SKILL_RANK_LEADER_ID = uuid.uuid4()
SKILL_RANK_NON_LEADER_ID = uuid.uuid4()

DEFAULT_RULES = ShiftRulesConfig(
    min_interval_days=10,
    require_skill_ranks=["rank_a"],
    allow_same_department=False,
    special_employment_shifts=["weekday_night"],
    workers_per_slot=2,
)


def _make_requirement(
    *,
    req_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    shift_date_str: str = "2099-06-01",
    slot_type: str = "weekday_night",
    required_headcount: int = 2,
) -> ShiftRequirement:
    """テスト用ShiftRequirementオブジェクトを生成するヘルパー."""
    from datetime import date

    r = ShiftRequirement()
    r.id = req_id or REQ_ID
    r.tenant_id = tenant_id
    r.department_id = uuid.uuid4()
    r.shift_date = date.fromisoformat(shift_date_str)
    r.slot_type = slot_type  # type: ignore[assignment]
    r.required_headcount = required_headcount
    r.created_at = datetime(2026, 1, 1)
    r.updated_at = datetime(2026, 1, 1)
    return r


def _make_worker(
    *,
    worker_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    name: str = "テストワーカー",
    department_id: uuid.UUID | None = None,
    skill_rank_id: uuid.UUID | None = None,
    is_special: bool = False,
) -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = worker_id or WORKER_ID_1
    w.tenant_id = tenant_id
    w.name = name
    w.department_id = department_id or DEPT_A_ID
    w.skill_rank_id = skill_rank_id or SKILL_RANK_LEADER_ID
    w.is_special = is_special
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


# ---------------------------------------------------------------------------
# validate_shift_assignments
# ---------------------------------------------------------------------------


class TestValidateShiftAssignments:
    """validate_shift_assignments の各ルール検証テスト."""

    # --- 空入力 ---

    def test_empty_workers_returns_no_violations(self) -> None:
        """正常系: ワーカーが空の場合、違反なしを返す."""
        session = MagicMock()
        req = _make_requirement()
        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [], DEFAULT_RULES
        )
        assert result == []

    # --- ルール1: 1人1日1枠 ---

    def test_daily_duplicate_detected(self) -> None:
        """異常系（ルール1）: 同日に別枠へのアサインがある場合、DAILY_DUPLICATE を返す."""
        session = MagicMock()
        # first() で重複アサインが存在する（truthy）
        session.exec.return_value = MagicMock(**{"first.return_value": MagicMock()})
        req = _make_requirement()
        worker = _make_worker()

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "DAILY_DUPLICATE" in codes

    def test_no_daily_duplicate_when_no_other_assignment(self) -> None:
        """正常系（ルール1）: 同日に他のアサインがない場合、DAILY_DUPLICATE なし."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement()
        worker = _make_worker()

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "DAILY_DUPLICATE" not in codes

    # --- ルール2: 同一所属課ペア禁止 ---

    def test_same_department_detected(self) -> None:
        """異常系（ルール2）: 同じ所属課ワーカーが2名いる場合、SAME_DEPARTMENT を返す."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement()
        w1 = _make_worker(worker_id=WORKER_ID_1, department_id=DEPT_A_ID, name="A1")
        w2 = _make_worker(worker_id=WORKER_ID_2, department_id=DEPT_A_ID, name="A2")

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1, w2], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SAME_DEPARTMENT" in codes

    def test_different_departments_no_violation(self) -> None:
        """正常系（ルール2）: 異なる所属課の場合、SAME_DEPARTMENT なし."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement()
        w1 = _make_worker(worker_id=WORKER_ID_1, department_id=DEPT_A_ID)
        w2 = _make_worker(worker_id=WORKER_ID_2, department_id=DEPT_B_ID)

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1, w2], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SAME_DEPARTMENT" not in codes

    def test_same_department_allowed_when_rule_disabled(self) -> None:
        """正常系（ルール2）: allow_same_department=True の場合、違反なし."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement()
        w1 = _make_worker(worker_id=WORKER_ID_1, department_id=DEPT_A_ID, name="A1")
        w2 = _make_worker(worker_id=WORKER_ID_2, department_id=DEPT_A_ID, name="A2")
        rules = ShiftRulesConfig(**{**DEFAULT_RULES.model_dump(), "allow_same_department": True})

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1, w2], rules
        )

        codes = [v.code for v in result]
        assert "SAME_DEPARTMENT" not in codes

    # --- ルール3: スキルランクA必須 ---

    def test_missing_rank_a_detected(self) -> None:
        """異常系（ルール3）: リーダー適性のワーカーがいない場合、SKILL_RANK_A を返す."""
        session = MagicMock()
        # exec の呼び出し順: daily_duplicate for w1, daily_duplicate for w2, skill_rank check
        call_index = [0]

        def exec_side_effect(stmt: object) -> MagicMock:
            m = MagicMock()
            call_index[0] += 1
            idx = call_index[0]
            if idx in (1, 2):
                # ルール1: daily_duplicate（first → None = 重複なし）
                m.first.return_value = None
                m.all.return_value = []
            elif idx == 3:
                # ルール3: is_leader_eligible チェック（first → None = リーダーなし）
                m.first.return_value = None
                m.all.return_value = []
            else:
                m.first.return_value = None
                m.all.return_value = []
            return m

        session.exec.side_effect = exec_side_effect
        req = _make_requirement(required_headcount=2)
        w1 = _make_worker(
            worker_id=WORKER_ID_1,
            department_id=DEPT_A_ID,
            skill_rank_id=SKILL_RANK_NON_LEADER_ID,
        )
        w2 = _make_worker(
            worker_id=WORKER_ID_2,
            department_id=DEPT_B_ID,
            skill_rank_id=SKILL_RANK_NON_LEADER_ID,
        )

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1, w2], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SKILL_RANK_A" in codes

    def test_rank_a_present_no_violation(self) -> None:
        """正常系（ルール3）: リーダー適性のワーカーが含まれる場合、SKILL_RANK_A なし."""
        from app.models.models import TenantSkillRank

        leader_rank = TenantSkillRank()
        leader_rank.id = SKILL_RANK_LEADER_ID
        leader_rank.is_leader_eligible = True

        session = MagicMock()
        call_index = [0]

        def exec_side_effect(stmt: object) -> MagicMock:
            m = MagicMock()
            call_index[0] += 1
            idx = call_index[0]
            if idx == 1:
                # ルール1: daily_duplicate for w1（first → None = 重複なし）
                m.first.return_value = None
                m.all.return_value = []
            elif idx == 2:
                # ルール1: daily_duplicate for w2（first → None = 重複なし）
                m.first.return_value = None
                m.all.return_value = []
            elif idx == 3:
                # ルール3: is_leader_eligible チェック（first → leader_rank）
                m.first.return_value = leader_rank
                m.all.return_value = [leader_rank]
            else:
                m.first.return_value = None
                m.all.return_value = []
            return m

        session.exec.side_effect = exec_side_effect
        req = _make_requirement(required_headcount=2)
        w1 = _make_worker(
            worker_id=WORKER_ID_1,
            department_id=DEPT_A_ID,
            skill_rank_id=SKILL_RANK_LEADER_ID,
        )
        w2 = _make_worker(
            worker_id=WORKER_ID_2,
            department_id=DEPT_B_ID,
            skill_rank_id=SKILL_RANK_NON_LEADER_ID,
        )

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1, w2], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SKILL_RANK_A" not in codes

    def test_skill_rank_not_checked_when_headcount_not_met(self) -> None:
        """正常系（ルール3）: 必要人数未満の場合、スキルランク違反を検出しない."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement(required_headcount=2)
        # 1人だけ（required_headcount=2 に満たない）
        w1 = _make_worker(
            worker_id=WORKER_ID_1,
            department_id=DEPT_A_ID,
            skill_rank_id=SKILL_RANK_NON_LEADER_ID,
        )

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SKILL_RANK_A" not in codes

    # --- ルール4: 中N日以上の勤務間隔 ---

    def test_work_interval_violation_detected(self) -> None:
        """異常系（ルール4）: 中9日未満の間隔で別アサインがある場合、WORK_INTERVAL を返す."""
        session = MagicMock()
        other_req_id = uuid.uuid4()
        # 4日後（min_interval_days=10 未満）の requirement
        other_req = _make_requirement(req_id=other_req_id, shift_date_str="2099-06-05")

        # exec の呼び出し順を追跡するためのカウンター
        call_index = [0]

        def exec_side_effect(stmt: object) -> MagicMock:
            m = MagicMock()
            call_index[0] += 1
            idx = call_index[0]
            if idx == 1:
                # ルール1: 1人1日1枠チェック（first() → None = 重複なし）
                m.first.return_value = None
                m.all.return_value = []
            elif idx == 2:
                # ルール4: アサイン済み requirement_id リスト → [other_req_id]
                m.all.return_value = [other_req_id]
                m.first.return_value = None
            elif idx == 3:
                # ルール4: 対応する ShiftRequirement オブジェクト取得
                m.all.return_value = [other_req]
                m.first.return_value = None
            else:
                m.all.return_value = []
                m.first.return_value = None
            return m

        session.exec.side_effect = exec_side_effect
        req = _make_requirement(shift_date_str="2099-06-01")
        worker = _make_worker()

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "WORK_INTERVAL" in codes

    def test_work_interval_no_violation_when_no_other_assignments(self) -> None:
        """正常系（ルール4）: 他にアサインがない場合、WORK_INTERVAL なし."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement()
        worker = _make_worker()

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "WORK_INTERVAL" not in codes

    # --- ルール5: 特別雇用者の枠制限 ---

    def test_special_employment_violation_on_non_weekday(self) -> None:
        """異常系（ルール5）: 特別雇用者が weekday_night 以外の枠にアサインされた場合。"""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement(slot_type="sat_day")
        worker = _make_worker(is_special=True)

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SPECIAL_EMPLOYMENT" in codes

    def test_special_employment_no_violation_on_weekday_night(self) -> None:
        """正常系（ルール5）: 特別雇用者が weekday_night にアサインされた場合、違反なし."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement(slot_type="weekday_night")
        worker = _make_worker(is_special=True)

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SPECIAL_EMPLOYMENT" not in codes

    def test_non_special_worker_can_be_assigned_anywhere(self) -> None:
        """正常系（ルール5）: 通常雇用者はどの枠にもアサイン可能。"""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement(slot_type="sat_night")
        worker = _make_worker(is_special=False)

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        assert "SPECIAL_EMPLOYMENT" not in codes

    # --- 複合ルール ---

    def test_multiple_violations_returned(self) -> None:
        """異常系: 複数のルール違反がある場合、すべての違反を返す."""
        session = MagicMock()
        # ルール1: daily_duplicate なし, ルール3: リーダー適性なし（first → None）
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        # sat_day スロット + 特別雇用者 + 同一所属課
        req = _make_requirement(slot_type="sat_day", required_headcount=2)
        w1 = _make_worker(
            worker_id=WORKER_ID_1,
            department_id=DEPT_A_ID,
            skill_rank_id=SKILL_RANK_NON_LEADER_ID,
            is_special=True,
        )
        w2 = _make_worker(
            worker_id=WORKER_ID_2,
            department_id=DEPT_A_ID,
            skill_rank_id=SKILL_RANK_NON_LEADER_ID,
            is_special=False,
        )

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [w1, w2], DEFAULT_RULES
        )

        codes = [v.code for v in result]
        # 同一所属課・スキルランクA欠如・特別雇用者違反
        assert "SAME_DEPARTMENT" in codes
        assert "SKILL_RANK_A" in codes
        assert "SPECIAL_EMPLOYMENT" in codes

    def test_violation_severity_is_error(self) -> None:
        """正常系: 検出された違反の severity は error である."""
        session = MagicMock()
        session.exec.return_value = MagicMock(
            **{"first.return_value": None, "all.return_value": []}
        )
        req = _make_requirement(slot_type="sat_day", required_headcount=1)
        worker = _make_worker(is_special=True)

        result = shift_validation_service.validate_shift_assignments(
            session, TENANT_ID, req, [worker], DEFAULT_RULES
        )

        for v in result:
            assert v.severity == "error"
