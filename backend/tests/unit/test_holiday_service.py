# backend/tests/unit/test_holiday_service.py
"""holiday_service モジュールの単体テスト.

外部依存（DB, jpholiday）は ``unittest.mock`` でMock化する。
"""

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.models import TenantHoliday
from app.models.schemas import (
    TenantHolidayCreate,
    TenantHolidayResponse,
)
from app.services import holiday_service
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
HOLIDAY_ID = uuid.uuid4()


def _make_holiday(
    *,
    holiday_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    holiday_date: date = date(2026, 1, 1),
    name: str = "元日",
    is_long_holiday: bool = False,
) -> TenantHoliday:
    """テスト用TenantHolidayオブジェクトを生成するヘルパー."""
    h = TenantHoliday()
    h.id = holiday_id or HOLIDAY_ID
    h.tenant_id = tenant_id
    h.date = holiday_date
    h.name = name
    h.is_long_holiday = is_long_holiday
    h.created_at = datetime(2026, 1, 1)
    return h


def _make_session(
    *,
    exec_first_return: object = None,
    exec_all_return: list | None = None,
) -> MagicMock:
    """テスト用Sessionモックを生成するヘルパー."""
    session = MagicMock()
    exec_result = MagicMock()
    exec_result.first.return_value = exec_first_return
    exec_result.all.return_value = exec_all_return or []
    session.exec.return_value = exec_result
    return session


# ---------------------------------------------------------------------------
# list_holidays
# ---------------------------------------------------------------------------


class TestListHolidays:
    """list_holidays の正常系テスト."""

    def test_list_holidays_returns_all(self) -> None:
        """正常系: 全件取得でテナントの休日一覧を返す."""
        holidays = [
            _make_holiday(name="元日"),
            _make_holiday(holiday_date=date(2026, 1, 12), name="成人の日"),
        ]
        session = _make_session(exec_all_return=holidays)

        result = holiday_service.list_holidays(session, TENANT_ID)

        assert len(result) == 2
        assert all(isinstance(r, TenantHolidayResponse) for r in result)

    def test_list_holidays_empty(self) -> None:
        """正常系: 休日が存在しない場合、空リストを返す."""
        session = _make_session(exec_all_return=[])

        result = holiday_service.list_holidays(session, TENANT_ID)

        assert result == []

    def test_list_holidays_seeds_when_year_empty(self) -> None:
        """正常系: 対象年のデータが0件の場合、自動シーディングが呼ばれる."""
        session = MagicMock()

        # 最初の exec (year_records) は空を返し、2回目の exec (stmt) は1件返す
        holiday = _make_holiday()
        exec_result_empty = MagicMock()
        exec_result_empty.all.return_value = []
        exec_result_empty.first.return_value = None

        exec_result_with_data = MagicMock()
        exec_result_with_data.all.return_value = [holiday]

        session.exec.side_effect = [
            exec_result_empty,   # year_records (no data → seed)
            exec_result_empty,   # _seed_year_holidays: existing check per holiday (1st)
            exec_result_with_data,  # final query
        ]

        with patch.object(holiday_service._jp_holiday, "year_holidays") as mock_yh:
            mock_holiday = MagicMock()
            mock_holiday.date = date(2026, 1, 1)
            mock_holiday.name = "元日"
            mock_yh.return_value = [mock_holiday]

            result = holiday_service.list_holidays(session, TENANT_ID, year=2026)

        assert len(result) == 1
        mock_yh.assert_called_once_with(2026)

    def test_list_holidays_skips_seed_when_year_has_data(self) -> None:
        """正常系: 対象年のデータが存在する場合、シーディングをスキップする."""
        holidays = [_make_holiday()]
        session = MagicMock()

        exec_result_with_data = MagicMock()
        exec_result_with_data.all.return_value = holidays

        # 両方の exec が同じデータを返す
        session.exec.return_value = exec_result_with_data

        with patch.object(holiday_service._jp_holiday, "year_holidays") as mock_yh:
            result = holiday_service.list_holidays(session, TENANT_ID, year=2026)

        mock_yh.assert_not_called()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# create_holidays
# ---------------------------------------------------------------------------


class TestCreateHolidays:
    """create_holidays の正常系・異常系テスト."""

    def test_create_holidays_success(self) -> None:
        """正常系: 休日を作成して返す."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = None
        session.exec.return_value = exec_result

        data = [TenantHolidayCreate(date=date(2026, 8, 1), name="創立記念日")]

        def _refresh(obj: TenantHoliday) -> None:
            obj.id = HOLIDAY_ID
            obj.tenant_id = TENANT_ID
            obj.date = date(2026, 8, 1)
            obj.name = "創立記念日"
            obj.is_long_holiday = False
            obj.created_at = datetime(2026, 1, 1)

        session.refresh.side_effect = _refresh

        result = holiday_service.create_holidays(session, TENANT_ID, data)

        assert len(result) == 1
        assert isinstance(result[0], TenantHolidayResponse)
        assert result[0].name == "創立記念日"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_create_holidays_conflict(self) -> None:
        """異常系: 同一日付のレコードが既に存在する場合、409例外を送出する."""
        existing = _make_holiday()
        session = _make_session(exec_first_return=existing)

        data = [TenantHolidayCreate(date=date(2026, 1, 1), name="元日")]

        with pytest.raises(HTTPException) as exc_info:
            holiday_service.create_holidays(session, TENANT_ID, data)

        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# delete_holiday
# ---------------------------------------------------------------------------


class TestDeleteHoliday:
    """delete_holiday の正常系・異常系テスト."""

    def test_delete_holiday_success(self) -> None:
        """正常系: 休日が存在する場合、物理削除を実行する."""
        holiday = _make_holiday()
        session = _make_session(exec_first_return=holiday)

        holiday_service.delete_holiday(session, TENANT_ID, HOLIDAY_ID)

        session.delete.assert_called_once_with(holiday)
        session.commit.assert_called_once()

    def test_delete_holiday_not_found(self) -> None:
        """異常系: 休日が存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            holiday_service.delete_holiday(session, TENANT_ID, HOLIDAY_ID)

        assert exc_info.value.status_code == 404
