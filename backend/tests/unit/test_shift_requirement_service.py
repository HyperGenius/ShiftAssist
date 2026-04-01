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
        """正常系: テナントに属するShiftRequirement一覧を返す."""
        reqs = [_make_req(required_headcount=1), _make_req(required_headcount=3)]
        session = _make_session(exec_all_return=reqs)

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
