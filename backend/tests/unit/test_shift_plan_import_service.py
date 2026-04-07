# backend/tests/unit/test_shift_plan_import_service.py
"""shift_plan_import_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import json
import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import HTTPException

from app.models.models import (
    PlanStatusEnum,
    ShiftAssignment,
    ShiftPlan,
    ShiftSlot,
    SlotTypeEnum,
    Worker,
)
from app.services import shift_plan_import_service

# ---------------------------------------------------------------------------
# テスト定数
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
TARGET_YM = "2025-12"
WORKER_EMP_NO_1 = "1234567"
WORKER_EMP_NO_2 = "1357926"
WORKER_ID_1 = uuid.uuid4()
WORKER_ID_2 = uuid.uuid4()


def _make_worker(employee_code: str, worker_id: uuid.UUID) -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = worker_id
    w.tenant_id = TENANT_ID
    w.employee_code = employee_code
    w.name = f"ワーカー{employee_code}"
    w.department_id = uuid.uuid4()
    w.is_special = False
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


# ---------------------------------------------------------------------------
# _parse_csv_bytes
# ---------------------------------------------------------------------------


class TestParseCsvBytes:
    """_parse_csv_bytes のテスト."""

    def test_valid_csv_returns_rows(self) -> None:
        """正常系: 有効なCSVを正しくパースして行辞書リストを返す."""
        csv_content = (
            "date,slot_type,worker_id_1,worker_id_2\n"
            "2025-12-01,weekday_night,1234567,1357926\n"
        ).encode("utf-8")

        rows = shift_plan_import_service._parse_csv_bytes(csv_content)

        assert len(rows) == 1
        assert rows[0]["date"] == "2025-12-01"
        assert rows[0]["slot_type"] == "weekday_night"
        assert rows[0]["worker_id_1"] == "1234567"
        assert rows[0]["worker_id_2"] == "1357926"

    def test_utf8_bom_csv_is_parsed(self) -> None:
        """正常系: UTF-8 BOM付きCSVを正しくパースする."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "2025-12-01,weekday_night,1234567\n"
        ).encode("utf-8-sig")

        rows = shift_plan_import_service._parse_csv_bytes(csv_content)
        assert len(rows) == 1

    def test_missing_required_columns_raises_422(self) -> None:
        """異常系: 必須列が不足している場合、422例外を送出する."""
        csv_content = "worker_id_1\n1234567\n".encode("utf-8")

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service._parse_csv_bytes(csv_content)

        assert exc_info.value.status_code == 422

    def test_empty_csv_returns_empty_list(self) -> None:
        """正常系: ヘッダーのみのCSVは空リストを返す."""
        csv_content = "date,slot_type,worker_id_1\n".encode("utf-8")

        rows = shift_plan_import_service._parse_csv_bytes(csv_content)
        assert rows == []


# ---------------------------------------------------------------------------
# _parse_json_bytes
# ---------------------------------------------------------------------------


class TestParseJsonBytes:
    """_parse_json_bytes のテスト."""

    def test_valid_json_returns_rows(self) -> None:
        """正常系: 有効なJSONをパースして行辞書リストを返す."""
        data = [
            {
                "date": "2025-12-01",
                "slot_type": "weekday_night",
                "worker_ids": ["1234567", "1357926"],
            }
        ]
        content = json.dumps(data).encode("utf-8")

        rows = shift_plan_import_service._parse_json_bytes(content)

        assert len(rows) == 1
        assert rows[0]["date"] == "2025-12-01"

    def test_invalid_json_raises_422(self) -> None:
        """異常系: 不正なJSONの場合、422例外を送出する."""
        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service._parse_json_bytes(b"not json")

        assert exc_info.value.status_code == 422

    def test_non_list_json_raises_422(self) -> None:
        """異常系: ルートがリストでない場合、422例外を送出する."""
        content = json.dumps({"date": "2025-12-01"}).encode("utf-8")

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service._parse_json_bytes(content)

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# _parse_date_str
# ---------------------------------------------------------------------------


class TestParseDateStr:
    """_parse_date_str のテスト."""

    def test_valid_date_returns_date_object(self) -> None:
        """正常系: YYYY-MM-DD形式を正しくパースする."""
        result = shift_plan_import_service._parse_date_str("2025-12-01", 0)
        assert result == date(2025, 12, 1)

    def test_invalid_date_raises_422(self) -> None:
        """異常系: 不正な日付形式の場合、422例外を送出する."""
        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service._parse_date_str("01/12/2025", 0)

        assert exc_info.value.status_code == 422

    def test_whitespace_is_stripped(self) -> None:
        """正常系: 前後の空白は除去して処理する."""
        result = shift_plan_import_service._parse_date_str("  2025-12-01  ", 0)
        assert result == date(2025, 12, 1)


# ---------------------------------------------------------------------------
# _parse_slot_type
# ---------------------------------------------------------------------------


class TestParseSlotType:
    """_parse_slot_type のテスト."""

    def test_valid_slot_type_returns_enum(self) -> None:
        """正常系: 有効な枠種別文字列をEnumに変換する."""
        result = shift_plan_import_service._parse_slot_type("weekday_night", 0)
        assert result == SlotTypeEnum.weekday_night

    def test_all_valid_slot_types(self) -> None:
        """正常系: 全ての有効な枠種別を正しく変換できる."""
        for slot_type in SlotTypeEnum:
            result = shift_plan_import_service._parse_slot_type(slot_type.value, 0)
            assert result == slot_type

    def test_invalid_slot_type_raises_422(self) -> None:
        """異常系: 不正な枠種別の場合、422例外を送出する."""
        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service._parse_slot_type("invalid_type", 0)

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# _extract_worker_ids_from_csv_row
# ---------------------------------------------------------------------------


class TestExtractWorkerIdsFromCsvRow:
    """_extract_worker_ids_from_csv_row のテスト."""

    def test_extracts_multiple_worker_ids(self) -> None:
        """正常系: 複数のworker_id列を正しく抽出する."""
        row = {
            "date": "2025-12-01",
            "slot_type": "weekday_night",
            "worker_id_1": "1234567",
            "worker_id_2": " 1357926 ",
        }
        result = shift_plan_import_service._extract_worker_ids_from_csv_row(row)
        assert "1234567" in result
        assert "1357926" in result

    def test_empty_worker_ids_are_excluded(self) -> None:
        """正常系: 空文字列のworker_idは除外される."""
        row = {
            "date": "2025-12-01",
            "slot_type": "weekday_night",
            "worker_id_1": "1234567",
            "worker_id_2": "",
        }
        result = shift_plan_import_service._extract_worker_ids_from_csv_row(row)
        assert result == ["1234567"]

    def test_no_worker_columns_returns_empty(self) -> None:
        """正常系: worker_id列がない場合、空リストを返す."""
        row = {"date": "2025-12-01", "slot_type": "weekday_night"}
        result = shift_plan_import_service._extract_worker_ids_from_csv_row(row)
        assert result == []


# ---------------------------------------------------------------------------
# import_shift_plan (統合テスト)
# ---------------------------------------------------------------------------


class TestImportShiftPlan:
    """import_shift_plan の正常系・異常系テスト."""

    def _make_session_mock(self, workers: list[Worker]) -> MagicMock:
        """テスト用セッションMockを生成するヘルパー."""
        session = MagicMock()
        session.exec.return_value = MagicMock(**{"all.return_value": workers})
        session.flush.return_value = None
        session.commit.return_value = None
        return session

    def test_import_csv_creates_plan_slots_assignments(self) -> None:
        """正常系: CSVインポートでShiftPlan/ShiftSlot/ShiftAssignmentが作成される."""
        csv_content = (
            "date,slot_type,worker_id_1,worker_id_2\n"
            "2025-12-01,weekday_night,1234567,1357926\n"
        ).encode("utf-8")

        workers = [
            _make_worker(WORKER_EMP_NO_1, WORKER_ID_1),
            _make_worker(WORKER_EMP_NO_2, WORKER_ID_2),
        ]
        session = self._make_session_mock(workers)

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
        )

        assert result.target_year_month == TARGET_YM
        assert result.status == PlanStatusEnum.published
        assert result.slots_created == 1
        assert result.assignments_created == 2
        assert result.skipped_worker_ids == []
        session.commit.assert_called_once()

    def test_import_json_creates_plan_slots_assignments(self) -> None:
        """正常系: JSONインポートでShiftPlan/ShiftSlot/ShiftAssignmentが作成される."""
        data = [
            {
                "date": "2025-12-01",
                "slot_type": "weekday_night",
                "worker_ids": [WORKER_EMP_NO_1],
            }
        ]
        json_content = json.dumps(data).encode("utf-8")

        workers = [_make_worker(WORKER_EMP_NO_1, WORKER_ID_1)]
        session = self._make_session_mock(workers)

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=json_content,
            content_type="json",
        )

        assert result.slots_created == 1
        assert result.assignments_created == 1
        session.commit.assert_called_once()

    def test_missing_worker_is_skipped(self) -> None:
        """正常系: 存在しない社員番号はスキップされ、skipped_worker_idsに含まれる."""
        csv_content = (
            "date,slot_type,worker_id_1,worker_id_2\n"
            "2025-12-01,weekday_night,1234567,9999999\n"
        ).encode("utf-8")

        # worker 9999999 は存在しない
        workers = [_make_worker(WORKER_EMP_NO_1, WORKER_ID_1)]
        session = self._make_session_mock(workers)

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
        )

        assert result.assignments_created == 1
        assert "9999999" in result.skipped_worker_ids

    def test_assignments_have_manual_override_true(self) -> None:
        """正常系: 全アサインに is_manual_override=True が設定される."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "2025-12-01,weekday_night,1234567\n"
        ).encode("utf-8")

        workers = [_make_worker(WORKER_EMP_NO_1, WORKER_ID_1)]
        session = self._make_session_mock(workers)

        shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
        )

        added_assignments = [
            call_args[0][0]
            for call_args in session.add.call_args_list
            if isinstance(call_args[0][0], ShiftAssignment)
        ]
        assert len(added_assignments) == 1
        assert added_assignments[0].is_manual_override is True

    def test_custom_plan_status(self) -> None:
        """正常系: plan_statusを指定してシフトプランを作成できる."""
        csv_content = (
            "date,slot_type\n"
            "2025-12-01,weekday_night\n"
        ).encode("utf-8")

        session = self._make_session_mock([])

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
            plan_status=PlanStatusEnum.draft,
        )

        assert result.status == PlanStatusEnum.draft

    def test_empty_file_raises_422(self) -> None:
        """異常系: データ行がないファイルの場合、422例外を送出する."""
        csv_content = "date,slot_type,worker_id_1\n".encode("utf-8")
        session = self._make_session_mock([])

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service.import_shift_plan(
                session=session,
                tenant_id=TENANT_ID,
                file_content=csv_content,
                content_type="csv",
            )

        assert exc_info.value.status_code == 422

    def test_invalid_date_raises_422(self) -> None:
        """異常系: 不正な日付フォーマットの場合、422例外を送出する（ロールバックあり）."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "bad-date,weekday_night,1234567\n"
        ).encode("utf-8")

        session = self._make_session_mock([])

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service.import_shift_plan(
                session=session,
                tenant_id=TENANT_ID,
                file_content=csv_content,
                content_type="csv",
            )

        assert exc_info.value.status_code == 422

    def test_invalid_slot_type_raises_422(self) -> None:
        """異常系: 不正な枠種別の場合、422例外を送出する."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "2025-12-01,unknown_type,1234567\n"
        ).encode("utf-8")

        session = self._make_session_mock([])

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service.import_shift_plan(
                session=session,
                tenant_id=TENANT_ID,
                file_content=csv_content,
                content_type="csv",
            )

        assert exc_info.value.status_code == 422

    def test_db_error_triggers_rollback(self) -> None:
        """異常系: DBエラーが発生した場合、ロールバックされ500例外を送出する."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "2025-12-01,weekday_night,1234567\n"
        ).encode("utf-8")

        workers = [_make_worker(WORKER_EMP_NO_1, WORKER_ID_1)]
        session = self._make_session_mock(workers)
        session.flush.side_effect = Exception("DB接続エラー")

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service.import_shift_plan(
                session=session,
                tenant_id=TENANT_ID,
                file_content=csv_content,
                content_type="csv",
            )

        assert exc_info.value.status_code == 500
        session.rollback.assert_called_once()

    def test_multiple_rows_multiple_slots(self) -> None:
        """正常系: 複数行のCSVで複数のShiftSlotが作成される."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "2025-12-01,weekday_night,1234567\n"
            "2025-12-02,sat_day,1234567\n"
            "2025-12-03,sun_hol_day,1234567\n"
        ).encode("utf-8")

        workers = [_make_worker(WORKER_EMP_NO_1, WORKER_ID_1)]
        session = self._make_session_mock(workers)

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
        )

        assert result.slots_created == 3
        assert result.assignments_created == 3

    def test_duplicate_worker_in_same_row_deduplicated(self) -> None:
        """正常系: 同一行に同一ワーカーが重複指定されても1件のアサインのみ作成される."""
        csv_content = (
            "date,slot_type,worker_id_1,worker_id_2\n"
            "2025-12-01,weekday_night,1234567,1234567\n"
        ).encode("utf-8")

        workers = [_make_worker(WORKER_EMP_NO_1, WORKER_ID_1)]
        session = self._make_session_mock(workers)

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
        )

        assert result.assignments_created == 1

    def test_mixed_months_raises_422(self) -> None:
        """異常系: 複数の年月が混在している場合、422例外を送出する."""
        csv_content = (
            "date,slot_type,worker_id_1\n"
            "2025-12-01,weekday_night,1234567\n"
            "2026-01-05,weekday_night,1234567\n"
        ).encode("utf-8")

        session = self._make_session_mock([])

        with pytest.raises(HTTPException) as exc_info:
            shift_plan_import_service.import_shift_plan(
                session=session,
                tenant_id=TENANT_ID,
                file_content=csv_content,
                content_type="csv",
            )

        assert exc_info.value.status_code == 422
        assert "複数の年月" in exc_info.value.detail

    def test_target_year_month_auto_detected(self) -> None:
        """正常系: 対象年月がファイル内の日付から自動検出される."""
        csv_content = (
            "date,slot_type\n"
            "2026-03-10,weekday_night\n"
            "2026-03-15,sat_day\n"
        ).encode("utf-8")

        session = self._make_session_mock([])

        result = shift_plan_import_service.import_shift_plan(
            session=session,
            tenant_id=TENANT_ID,
            file_content=csv_content,
            content_type="csv",
        )

        assert result.target_year_month == "2026-03"
