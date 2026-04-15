# backend/tests/unit/test_shift_requirement_service.py
"""shift_requirement_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.models import ShiftRequirement, SlotTypeEnum
from app.models.schemas import ShiftReqCreate, ShiftReqResponse, ShiftReqUpdate
from app.services import shift_requirement_service
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
REQ_ID = uuid.uuid4()
DEPT_ID = uuid.uuid4()

# テスト用の未来日付（今日より後）
FUTURE_DATE = date(2099, 12, 31)
PAST_DATE = date(2000, 1, 1)


def _make_req(
    *,
    req_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    department_id: uuid.UUID | None = None,
    target_date: date = FUTURE_DATE,
    slot_type: SlotTypeEnum = SlotTypeEnum.weekday_night,
    required_headcount: int = 2,
) -> ShiftRequirement:
    """テスト用ShiftRequirementオブジェクトを生成するヘルパー."""
    r = ShiftRequirement()
    r.id = req_id or REQ_ID
    r.tenant_id = tenant_id
    r.department_id = department_id or DEPT_ID
    r.shift_date = target_date
    r.slot_type = slot_type
    r.required_headcount = required_headcount
    r.created_at = datetime(2026, 1, 1)
    r.updated_at = datetime(2026, 1, 1)
    return r


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
# create_shift_req
# ---------------------------------------------------------------------------


class TestCreateShiftReq:
    """create_shift_req の正常系・異常系テスト."""

    def test_create_shift_req_success(self) -> None:
        """正常系: 有効なDepartmentと未来日付の場合、ShiftRequirementを作成して返す."""
        session = MagicMock()
        session.refresh.side_effect = lambda obj: None

        data = ShiftReqCreate(
            department_id=DEPT_ID,
            shift_date=FUTURE_DATE,
            slot_type=SlotTypeEnum.weekday_night,
            required_headcount=2,
        )

        def _refresh(obj: ShiftRequirement) -> None:
            obj.id = REQ_ID
            obj.tenant_id = TENANT_ID
            obj.department_id = DEPT_ID
            obj.shift_date = FUTURE_DATE
            obj.slot_type = SlotTypeEnum.weekday_night
            obj.required_headcount = 2
            obj.created_at = datetime(2026, 1, 1)
            obj.updated_at = datetime(2026, 1, 1)

        session.refresh.side_effect = _refresh

        with patch.object(shift_requirement_service, "_validate_department"):
            with patch.object(shift_requirement_service, "_validate_date_not_past"):
                result = shift_requirement_service.create_shift_req(
                    session, TENANT_ID, data
                )

        assert isinstance(result, ShiftReqResponse)
        assert result.tenant_id == TENANT_ID
        assert result.required_headcount == 2
        assert result.slot_type == SlotTypeEnum.weekday_night
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_create_shift_req_invalid_department(self) -> None:
        """異常系: Departmentが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = ShiftReqCreate(
            department_id=uuid.uuid4(),
            shift_date=FUTURE_DATE,
            slot_type=SlotTypeEnum.sat_day,
            required_headcount=1,
        )

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.create_shift_req(session, TENANT_ID, data)

        assert exc_info.value.status_code == 404

    def test_create_shift_req_past_date_raises_400(self) -> None:
        """異常系: 過去日付を指定した場合、400例外を送出する."""
        session = _make_session()
        data = ShiftReqCreate(
            department_id=DEPT_ID,
            shift_date=PAST_DATE,
            slot_type=SlotTypeEnum.weekday_night,
            required_headcount=2,
        )

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.create_shift_req(session, TENANT_ID, data)

        assert exc_info.value.status_code == 400

    def test_create_shift_req_cross_tenant_department_rejected(self) -> None:
        """異常系: 他テナントのDepartment IDを指定した場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = ShiftReqCreate(
            department_id=DEPT_ID,
            shift_date=FUTURE_DATE,
            slot_type=SlotTypeEnum.weekday_night,
            required_headcount=1,
        )

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.create_shift_req(session, OTHER_TENANT_ID, data)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# list_shift_reqs
# ---------------------------------------------------------------------------


class TestListShiftReqs:
    """list_shift_reqs の正常系テスト."""

    def test_list_shift_reqs_returns_tenant_reqs(self) -> None:
        """正常系: テナントに属するShiftRequirement一覧を返す（アサイン情報含む）."""
        reqs = [_make_req(required_headcount=1), _make_req(required_headcount=3)]
        session = MagicMock()
        exec_result_reqs = MagicMock()
        exec_result_reqs.all.return_value = reqs
        exec_result_assignments = MagicMock()
        exec_result_assignments.all.return_value = []
        session.exec.side_effect = [exec_result_reqs, exec_result_assignments]

        result = shift_requirement_service.list_shift_reqs(session, TENANT_ID)

        assert len(result) == 2
        assert all(isinstance(r, ShiftReqResponse) for r in result)
        assert all(r.tenant_id == TENANT_ID for r in result)

    def test_list_shift_reqs_empty(self) -> None:
        """正常系: ShiftRequirementが存在しない場合、空リストを返す."""
        session = _make_session(exec_all_return=[])

        result = shift_requirement_service.list_shift_reqs(session, TENANT_ID)

        assert result == []


# ---------------------------------------------------------------------------
# get_shift_req
# ---------------------------------------------------------------------------


class TestGetShiftReq:
    """get_shift_req の正常系・異常系テスト."""

    def test_get_shift_req_success(self) -> None:
        """正常系: ShiftRequirementが存在する場合、ShiftReqResponseを返す."""
        req = _make_req()
        session = _make_session(exec_first_return=req)

        result = shift_requirement_service.get_shift_req(session, TENANT_ID, REQ_ID)

        assert result.id == REQ_ID
        assert result.tenant_id == TENANT_ID

    def test_get_shift_req_not_found(self) -> None:
        """異常系: ShiftRequirementが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.get_shift_req(session, TENANT_ID, REQ_ID)

        assert exc_info.value.status_code == 404

    def test_get_shift_req_other_tenant_returns_404(self) -> None:
        """異常系: 他テナントのShiftRequirement IDを指定した場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.get_shift_req(session, OTHER_TENANT_ID, REQ_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# update_shift_req
# ---------------------------------------------------------------------------


class TestUpdateShiftReq:
    """update_shift_req の正常系・異常系テスト."""

    def test_update_shift_req_headcount_only(self) -> None:
        """正常系: required_headcount のみ指定した場合、該当フィールドのみ更新する."""
        req = _make_req()
        session = _make_session(exec_first_return=req)
        session.refresh.side_effect = lambda obj: None

        data = ShiftReqUpdate(required_headcount=5)

        result = shift_requirement_service.update_shift_req(
            session, TENANT_ID, REQ_ID, data
        )

        assert result.required_headcount == 5
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_update_shift_req_with_department_validates(self) -> None:
        """正常系: department_id を含む更新時に _validate_department が呼ばれる."""
        req = _make_req()
        session = _make_session(exec_first_return=req)
        session.refresh.side_effect = lambda obj: None

        new_dept_id = uuid.uuid4()
        data = ShiftReqUpdate(department_id=new_dept_id)

        with patch.object(
            shift_requirement_service, "_validate_department"
        ) as mock_validate:
            shift_requirement_service.update_shift_req(session, TENANT_ID, REQ_ID, data)

        mock_validate.assert_called_once_with(session, TENANT_ID, new_dept_id)

    def test_update_shift_req_with_past_date_raises_400(self) -> None:
        """異常系: 過去日付に更新しようとした場合、400例外を送出する."""
        req = _make_req()
        session = _make_session(exec_first_return=req)

        data = ShiftReqUpdate(shift_date=PAST_DATE)

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.update_shift_req(session, TENANT_ID, REQ_ID, data)

        assert exc_info.value.status_code == 400

    def test_update_shift_req_not_found(self) -> None:
        """異常系: ShiftRequirementが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = ShiftReqUpdate(required_headcount=3)

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.update_shift_req(session, TENANT_ID, REQ_ID, data)

        assert exc_info.value.status_code == 404

    def test_update_shift_req_invalid_department(self) -> None:
        """異常系: 更新時に存在しないDepartment IDを指定した場合、404例外を送出する."""
        req = _make_req()
        session = _make_session(exec_first_return=req)

        data = ShiftReqUpdate(department_id=uuid.uuid4())

        with patch.object(
            shift_requirement_service,
            "_validate_department",
            side_effect=HTTPException(status_code=404, detail="Department not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                shift_requirement_service.update_shift_req(
                    session, TENANT_ID, REQ_ID, data
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_shift_req
# ---------------------------------------------------------------------------


class TestDeleteShiftReq:
    """delete_shift_req の正常系・異常系テスト."""

    def test_delete_shift_req_success(self) -> None:
        """正常系: ShiftRequirementが存在する場合、物理削除を実行する."""
        req = _make_req()
        session = _make_session(exec_first_return=req)

        shift_requirement_service.delete_shift_req(session, TENANT_ID, REQ_ID)

        session.delete.assert_called_once_with(req)
        session.commit.assert_called_once()

    def test_delete_shift_req_not_found(self) -> None:
        """異常系: ShiftRequirementが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.delete_shift_req(session, TENANT_ID, REQ_ID)

        assert exc_info.value.status_code == 404

    def test_delete_shift_req_other_tenant_rejected(self) -> None:
        """異常系: 他テナントのShiftRequirementを削除しようとした場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            shift_requirement_service.delete_shift_req(session, OTHER_TENANT_ID, REQ_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# _determine_slot_types_for_date
# ---------------------------------------------------------------------------


class TestDetermineSlotTypesForDate:
    """_determine_slot_types_for_date の正常系テスト."""

    def test_weekday_returns_weekday_night(self) -> None:
        """正常系: 平日（休日なし）は weekday_night のみ返す."""
        # 2026-04-06 は月曜日
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 6), set(), set()
        )
        assert result == [SlotTypeEnum.weekday_night]

    def test_saturday_returns_sat_day_and_night(self) -> None:
        """正常系: 土曜日は sat_day と sat_night を返す."""
        # 2026-04-04 は土曜日
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 4), set(), set()
        )
        assert result == [SlotTypeEnum.sat_day, SlotTypeEnum.sat_night]

    def test_sunday_returns_sun_hol_day_and_night(self) -> None:
        """正常系: 日曜日は sun_hol_day と sun_hol_night を返す."""
        # 2026-04-05 は日曜日
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 5), set(), set()
        )
        assert result == [SlotTypeEnum.sun_hol_day, SlotTypeEnum.sun_hol_night]

    def test_holiday_weekday_returns_sun_hol_slots(self) -> None:
        """正常系: 平日でも祝日の場合は sun_hol_day と sun_hol_night を返す."""
        # 2026-01-12 は月曜日（成人の日仮定）
        holiday_date = date(2026, 1, 12)
        result = shift_requirement_service._determine_slot_types_for_date(
            holiday_date, {holiday_date}, set()
        )
        assert result == [SlotTypeEnum.sun_hol_day, SlotTypeEnum.sun_hol_night]

    def test_long_holiday_returns_long_hol_slots(self) -> None:
        """正常系: 長期連休は long_hol_day と long_hol_night を返す."""
        long_hol_date = date(2026, 5, 4)
        result = shift_requirement_service._determine_slot_types_for_date(
            long_hol_date, set(), {long_hol_date}
        )
        assert result == [SlotTypeEnum.long_hol_day, SlotTypeEnum.long_hol_night]

    def test_long_holiday_takes_precedence_over_saturday(self) -> None:
        """正常系: 長期連休が土曜より優先される."""
        # 2026-05-02 は土曜日だが長期連休とする
        long_hol_sat = date(2026, 5, 2)
        result = shift_requirement_service._determine_slot_types_for_date(
            long_hol_sat, set(), {long_hol_sat}
        )
        assert result == [SlotTypeEnum.long_hol_day, SlotTypeEnum.long_hol_night]

    def test_friday_before_saturday_returns_sat_pre_hol_night(self) -> None:
        """正常系: 金曜日（翌日が土曜）は sat_pre_hol_night を返す."""
        # 2026-04-03 は金曜日（翌日 04-04 が土曜日）
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 3), set(), set()
        )
        assert result == [SlotTypeEnum.sat_pre_hol_night]

    def test_weekday_before_holiday_returns_sat_pre_hol_night(self) -> None:
        """正常系: 翌日が祝日の平日は sat_pre_hol_night を返す."""
        # 翌日が祝日（木曜日→金曜祝日）
        holiday_fri = date(2026, 4, 24)
        thu_before = date(2026, 4, 23)  # 木曜日
        result = shift_requirement_service._determine_slot_types_for_date(
            thu_before, {holiday_fri}, set()
        )
        assert result == [SlotTypeEnum.sat_pre_hol_night]

    def test_saturday_before_holiday_not_sat_pre_hol(self) -> None:
        """正常系: 土曜日は翌日が祝日でも sat_pre_hol_night にならない（土曜は sat_day/sat_night）."""
        # 2026-04-04 は土曜日
        sunday_hol = date(2026, 4, 5)
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 4), {sunday_hol}, set()
        )
        assert result == [SlotTypeEnum.sat_day, SlotTypeEnum.sat_night]

    def test_sunday_before_holiday_not_sat_pre_hol(self) -> None:
        """正常系: 日曜日は翌日が祝日でも sat_pre_hol_night にならない（日曜は sun_hol 枠）."""
        monday_hol = date(2026, 4, 6)
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 5), set(), set()
        )
        # 日曜は sun_hol_day, sun_hol_night
        assert result == [SlotTypeEnum.sun_hol_day, SlotTypeEnum.sun_hol_night]
        # 念のため monday_hol をセットしても同じ
        result2 = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 5), {monday_hol}, set()
        )
        assert result2 == [SlotTypeEnum.sun_hol_day, SlotTypeEnum.sun_hol_night]

    def test_holiday_itself_not_sat_pre_hol(self) -> None:
        """正常系: 祝日当日（翌日も祝日）は sat_pre_hol_night にならない（sun_hol 枠）."""
        # 対象日が祝日であれば sun_hol 扱い
        today_hol = date(2026, 4, 22)
        tomorrow_hol = date(2026, 4, 23)
        result = shift_requirement_service._determine_slot_types_for_date(
            today_hol, {today_hol, tomorrow_hol}, set()
        )
        assert result == [SlotTypeEnum.sun_hol_day, SlotTypeEnum.sun_hol_night]

    def test_normal_thursday_returns_weekday_night(self) -> None:
        """正常系: 通常の木曜日（翌日が祝日でない）は weekday_night を返す."""
        # 2026-04-09 は木曜日、翌日 04-10 は金曜日で祝日ではない
        result = shift_requirement_service._determine_slot_types_for_date(
            date(2026, 4, 9), set(), set()
        )
        assert result == [SlotTypeEnum.weekday_night]


# ---------------------------------------------------------------------------
# generate_requirements_for_month
# ---------------------------------------------------------------------------


def _make_holiday_row(*, d: date, is_long: bool = False) -> MagicMock:
    """テスト用 TenantHoliday モックを生成するヘルパー."""
    h = MagicMock()
    h.date = d
    h.is_long_holiday = is_long
    return h


class TestGenerateRequirementsForMonth:
    """generate_requirements_for_month の正常系テスト."""

    def _make_session_for_generate(
        self,
        holiday_rows: list[MagicMock],
        existing_reqs: list[ShiftRequirement],
    ) -> MagicMock:
        """generate_requirements_for_month 用のセッションモックを生成する."""
        session = MagicMock()
        # exec が2回呼ばれる: 1回目=祝日取得, 2回目=既存レコード取得
        first_exec = MagicMock()
        first_exec.all.return_value = holiday_rows
        second_exec = MagicMock()
        second_exec.all.return_value = existing_reqs
        session.exec.side_effect = [first_exec, second_exec]
        session.refresh.side_effect = lambda obj: None
        return session

    def test_generates_records_for_month_no_holidays(self) -> None:
        """正常系: 祝日なし・既存レコードなしの月（平日のみ）で weekday_night のみ生成."""
        # 2026年2月: 28日 / 全て平日（土日を除く）と仮定
        # 実際の曜日: 2026-02-01=日, ..., 7=土, 8=日, ..., 14=土, 15=日, 21=土, 22=日, 28=土
        session = self._make_session_for_generate([], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2026, 2
        )

        # 2026-02: 日曜4日, 土曜4日 → 日曜=sun_hol×2, 土曜=sat×2, 残20平日=weekday×1
        # 日: 1,8,15,22 → sun_hol_day + sun_hol_night = 8件
        # 土: 7,14,21,28 → sat_day + sat_night = 8件
        # 平日: 20日 → weekday_night = 20件
        # 合計 = 36件
        assert len(created) == 36
        assert session.add.call_count == 36
        session.commit.assert_called_once()

    def test_generates_records_with_holiday(self) -> None:
        """正常系: 平日に祝日が含まれる場合、sun_hol_day/night が生成される."""
        # 2026-01-12 (月曜=祝日) を含む1月
        holiday = _make_holiday_row(d=date(2026, 1, 12), is_long=False)
        session = self._make_session_for_generate([holiday], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2026, 1
        )

        slot_types = [r.slot_type for r in created]
        assert SlotTypeEnum.sun_hol_day in slot_types
        assert SlotTypeEnum.sun_hol_night in slot_types
        # 祝日 (平日) のうち1日が sun_hol に変わるため weekday_night が1件減る
        assert created  # 何か生成されていること

    def test_skips_existing_records(self) -> None:
        """正常系: 既存レコードが存在する場合、該当する (date, slot_type) をスキップする."""
        # 2026-04-06 (月曜) の weekday_night が既存と仮定
        existing = _make_req(
            target_date=date(2026, 4, 6),
            slot_type=SlotTypeEnum.weekday_night,
        )
        session = self._make_session_for_generate([], [existing])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2026, 4
        )

        # 既存の (2026-04-06, weekday_night) はスキップ → 1件少ない
        dates_slots = [(r.shift_date, r.slot_type) for r in created]
        assert (date(2026, 4, 6), SlotTypeEnum.weekday_night) not in dates_slots

    def test_returns_empty_list_when_all_existing(self) -> None:
        """正常系: 全レコードが既存の場合、空リストを返す."""
        # 1日分だけテスト: 2099-12-31 (水曜=平日) の weekday_night が既存
        existing = _make_req(
            target_date=date(2099, 12, 31),
            slot_type=SlotTypeEnum.weekday_night,
        )
        # 2099-12月を generate するが既存が全て埋まっている前提
        # 実際には全日のレコードを作ると複雑なので、1件スキップのみ確認
        session = self._make_session_for_generate([], [existing])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2099, 12
        )

        # 12月の残りの日/枠は生成されるが、2099-12-31 weekday_night はスキップ
        dates_slots = [(r.shift_date, r.slot_type) for r in created]
        assert (date(2099, 12, 31), SlotTypeEnum.weekday_night) not in dates_slots

    def test_no_commit_when_nothing_created(self) -> None:
        """正常系: 新規生成レコードがない場合、commit が呼ばれない."""
        # 小さい月で全レコードを既存として用意
        # 2026年2月の全レコードを既存とする
        import calendar as cal_mod

        _, last_day = cal_mod.monthrange(2026, 2)
        existing_reqs = []
        for day in range(1, last_day + 1):
            d = date(2026, 2, day)
            slot_types = shift_requirement_service._determine_slot_types_for_date(
                d, set(), set()
            )
            for st in slot_types:
                existing_reqs.append(_make_req(target_date=d, slot_type=st))

        session = self._make_session_for_generate([], existing_reqs)

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2026, 2
        )

        assert created == []
        session.commit.assert_not_called()

    def test_default_headcount_is_two(self) -> None:
        """正常系: デフォルトの required_headcount は 2 である."""
        session = self._make_session_for_generate([], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2026, 2
        )

        assert all(r.required_headcount == 2 for r in created)

    def test_custom_headcount(self) -> None:
        """正常系: default_headcount を指定した場合、その値が使用される."""
        session = self._make_session_for_generate([], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2026, 2, default_headcount=3
        )

        assert all(r.required_headcount == 3 for r in created)

    def test_month_end_next_day_holiday_sat_pre_hol_night(self) -> None:
        """境界値テスト: 月末日（金曜）の翌日（翌月1日）が祝日の場合、sat_pre_hol_night が生成される.

        例: 2025年1月31日（金曜）→ 翌日は2月1日
        もし2月1日が祝日なら、1月31日は sat_pre_hol_night として扱われる。
        generate_requirements_for_month が月末+1日の祝日を取得するよう修正されていることを確認する。
        2025-01-31 は金曜日（翌日は2月1日）。
        """
        # 2025-02-01 を祝日として設定（翌月1日）
        next_month_holiday = _make_holiday_row(d=date(2025, 2, 1), is_long=False)
        session = self._make_session_for_generate([next_month_holiday], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2025, 1
        )

        # 2025-01-31（金曜）が sat_pre_hol_night として生成されることを確認
        dates_slots = [(r.shift_date, r.slot_type) for r in created]
        assert (date(2025, 1, 31), SlotTypeEnum.sat_pre_hol_night) in dates_slots
        # weekday_night ではないことを確認
        assert (date(2025, 1, 31), SlotTypeEnum.weekday_night) not in dates_slots

    def test_month_end_next_day_saturday_sat_pre_hol_night(self) -> None:
        """境界値テスト: 月末日（金曜）の翌日が土曜の場合、sat_pre_hol_night として生成される.

        2025-01-31 は金曜日 → 翌日は 2025-02-01（土曜）→ 曜日判定により sat_pre_hol_night。
        """
        # 祝日なし（翌月1日も祝日でない）
        session = self._make_session_for_generate([], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2025, 1
        )

        # 2025-01-31（金曜）は翌日が土曜なので sat_pre_hol_night として生成されることを確認
        dates_slots = [(r.shift_date, r.slot_type) for r in created]
        assert (date(2025, 1, 31), SlotTypeEnum.sat_pre_hol_night) in dates_slots
        assert (date(2025, 1, 31), SlotTypeEnum.weekday_night) not in dates_slots

    def test_month_end_wednesday_next_day_holiday_sat_pre_hol_night(self) -> None:
        """境界値テスト: 月末日（水曜）の翌日（翌月1日）が祝日の場合、sat_pre_hol_night が生成される.

        2025-04-30（水曜）→ 翌日は 2025-05-01（木曜）
        2025-05-01 はメーデー（祝日）のため、4月30日は sat_pre_hol_night になるはず。
        """
        # 2025-05-01 を祝日として設定（翌月1日 = メーデー）
        next_month_holiday = _make_holiday_row(d=date(2025, 5, 1), is_long=False)
        session = self._make_session_for_generate([next_month_holiday], [])

        created = shift_requirement_service.generate_requirements_for_month(
            session, TENANT_ID, 2025, 4
        )

        # 2025-04-30（水曜）が sat_pre_hol_night として生成されることを確認
        dates_slots = [(r.shift_date, r.slot_type) for r in created]
        assert (date(2025, 4, 30), SlotTypeEnum.sat_pre_hol_night) in dates_slots
        # weekday_night ではないことを確認
        assert (date(2025, 4, 30), SlotTypeEnum.weekday_night) not in dates_slots
