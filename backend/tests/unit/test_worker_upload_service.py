# backend/tests/unit/test_worker_upload_service.py
"""worker_upload_service の単体テスト."""

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.models import Branch, Department, Position, TenantSkillRank, Worker
from app.models.schemas import WorkerUploadPreviewResponse, WorkerUploadUpsertResponse
from app.services import worker_upload_service
from app.services.worker_upload_service import (
    _ParsedRow,
    _parse_bool,
    _parse_date,
    _parse_transfer_type,
    parse_csv_bytes,
)

# ---------------------------------------------------------------------------
# テスト用定数
# ---------------------------------------------------------------------------

TENANT_ID = "org_upload_test"
DEPT_ID_1 = uuid.uuid4()
POS_ID_1 = uuid.uuid4()
SR_ID_1 = uuid.uuid4()
WORKER_ID_1 = uuid.uuid4()


# ---------------------------------------------------------------------------
# パーサユーティリティ
# ---------------------------------------------------------------------------


class TestParseDateUtil:
    """_parse_date の単体テスト."""

    def test_valid_dash_format(self) -> None:
        """YYYY-MM-DD形式をパースできる."""
        assert _parse_date("2000-04-01", "生年月日") == date(2000, 4, 1)

    def test_valid_slash_format(self) -> None:
        """YYYY/MM/DD形式をパースできる."""
        assert _parse_date("2000/04/01", "生年月日") == date(2000, 4, 1)

    def test_empty_returns_none(self) -> None:
        """空文字列はNoneを返す."""
        assert _parse_date("", "生年月日") is None

    def test_whitespace_returns_none(self) -> None:
        """空白文字列はNoneを返す."""
        assert _parse_date("  ", "生年月日") is None

    def test_invalid_format_raises(self) -> None:
        """不正なフォーマットはValueErrorを送出する."""
        with pytest.raises(ValueError, match="生年月日"):
            _parse_date("2000-13-01", "生年月日")

    def test_partial_date_raises(self) -> None:
        """部分的な日付はValueErrorを送出する."""
        with pytest.raises(ValueError):
            _parse_date("2000-04", "生年月日")


class TestParseBoolUtil:
    """_parse_bool の単体テスト."""

    def test_true_values(self) -> None:
        """Trueに相当する値を正しく変換する."""
        for v in ["あり", "true", "True", "1", "yes"]:
            assert _parse_bool(v, "事業本部変更の有無") is True

    def test_false_values(self) -> None:
        """Falseに相当する値を正しく変換する."""
        for v in ["なし", "false", "False", "0", "no"]:
            assert _parse_bool(v, "事業本部変更の有無") is False

    def test_empty_returns_none(self) -> None:
        """空文字列はNoneを返す."""
        assert _parse_bool("", "事業本部変更の有無") is None

    def test_invalid_raises(self) -> None:
        """不正な値はValueErrorを送出する."""
        with pytest.raises(ValueError, match="不正です"):
            _parse_bool("不明", "事業本部変更の有無")


class TestParseTransferTypeUtil:
    """_parse_transfer_type の単体テスト."""

    def test_japanese_no_transfer(self) -> None:
        """「異動なし」をno_transferに変換する."""
        from app.models.models import TransferTypeEnum

        assert _parse_transfer_type("異動なし") == TransferTypeEnum.no_transfer

    def test_japanese_transfer_in(self) -> None:
        """「転入」をtransfer_inに変換する."""
        from app.models.models import TransferTypeEnum

        assert _parse_transfer_type("転入") == TransferTypeEnum.transfer_in

    def test_japanese_hired(self) -> None:
        """「採用」をhiredに変換する."""
        from app.models.models import TransferTypeEnum

        assert _parse_transfer_type("採用") == TransferTypeEnum.hired

    def test_english_hired(self) -> None:
        """「hired」をhiredに変換する."""
        from app.models.models import TransferTypeEnum

        assert _parse_transfer_type("hired") == TransferTypeEnum.hired

    def test_empty_returns_none(self) -> None:
        """空文字列はNoneを返す."""
        assert _parse_transfer_type("") is None

    def test_invalid_raises(self) -> None:
        """不正な値はValueErrorを送出する."""
        with pytest.raises(ValueError, match="異動種別"):
            _parse_transfer_type("不明な種別")


# ---------------------------------------------------------------------------
# CSV/Excelパース
# ---------------------------------------------------------------------------


class TestParseCsvBytes:
    """parse_csv_bytes の単体テスト."""

    def _make_csv(self, header: str, row: str) -> bytes:
        return f"{header}\n{row}\n".encode("utf-8-sig")

    def test_valid_csv(self) -> None:
        """正常なCSVをパースできる."""
        csv_bytes = self._make_csv("職員番号,氏名,役職名", "E001,田中 太郎,係長")
        rows = parse_csv_bytes(csv_bytes)
        assert len(rows) == 1
        assert rows[0]["職員番号"] == "E001"
        assert rows[0]["氏名"] == "田中 太郎"

    def test_missing_required_col_raises(self) -> None:
        """必須列が不足している場合、HTTPExceptionを送出する."""
        csv_bytes = self._make_csv("氏名", "田中 太郎")
        with pytest.raises(HTTPException) as exc_info:
            parse_csv_bytes(csv_bytes)
        assert exc_info.value.status_code == 422
        assert "職員番号" in exc_info.value.detail

    def test_shift_jis_csv(self) -> None:
        """Shift-JISエンコードCSVをパースできる."""
        csv_bytes = "職員番号,氏名\nE001,田中 太郎\n".encode("shift_jis")
        rows = parse_csv_bytes(csv_bytes)
        assert rows[0]["職員番号"] == "E001"

    def test_invalid_encoding_raises(self) -> None:
        """認識できないエンコーディングの場合、HTTPExceptionを送出する."""
        with pytest.raises(HTTPException) as exc_info:
            parse_csv_bytes(b"\xff\xfe\x00\x00invalid")
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# preview_upload
# ---------------------------------------------------------------------------


def _make_dept(
    dept_id: uuid.UUID = DEPT_ID_1, name: str = "1課"
) -> Department:
    """テスト用Departmentを生成する."""
    d = Department()
    d.id = dept_id
    d.tenant_id = TENANT_ID
    d.name = name
    d.code = "dept_1"
    d.created_at = datetime(2026, 1, 1)
    d.deleted_at = None
    return d


def _make_worker(
    employee_code: str = "E001",
    name: str = "田中 太郎",
    department_id: uuid.UUID = DEPT_ID_1,
) -> Worker:
    """テスト用Workerを生成する."""
    w = Worker()
    w.id = WORKER_ID_1
    w.tenant_id = TENANT_ID
    w.employee_code = employee_code
    w.name = name
    w.department_id = department_id
    w.skill_rank_id = SR_ID_1
    w.is_special = False
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


def _make_session_mock(
    positions: list = (),
    branches: list = (),
    departments: list = (),
    skill_ranks: list = (),
    employment_types: list = (),
    workers: list = (),
) -> MagicMock:
    """指定したマスタデータを返すセッションMockを作成する."""
    session = MagicMock()
    results = [positions, branches, departments, skill_ranks, employment_types, workers]

    def make_exec_result(data: list) -> MagicMock:
        r = MagicMock()
        r.all.return_value = list(data)
        return r

    session.exec.side_effect = [make_exec_result(d) for d in results]
    return session


class TestPreviewUpload:
    """preview_upload の単体テスト."""

    def test_new_worker_shows_create(self) -> None:
        """新規Workerはcreateアクションで表示される."""
        dept = _make_dept()
        session = _make_session_mock(departments=[dept], workers=[])
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "課名": "1課"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert isinstance(result, WorkerUploadPreviewResponse)
        assert result.create_count == 1
        assert result.error_count == 0
        assert result.diff_items[0].action == "create"

    def test_existing_worker_changed_shows_update(self) -> None:
        """既存Workerの氏名変更はupdateアクションで表示される."""
        dept = _make_dept()
        existing = _make_worker(name="旧名前")
        session = _make_session_mock(departments=[dept], workers=[existing])
        raw_rows = [{"職員番号": "E001", "氏名": "新名前", "課名": "1課"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.update_count == 1
        assert result.diff_items[0].action == "update"
        assert result.diff_items[0].before is not None
        assert result.diff_items[0].before.name == "旧名前"
        assert result.diff_items[0].after.name == "新名前"

    def test_existing_worker_unchanged_shows_no_change(self) -> None:
        """既存Workerが変更なしの場合はno_changeアクションで表示される."""
        dept = _make_dept()
        existing = _make_worker(name="田中 太郎")
        session = _make_session_mock(departments=[dept], workers=[existing])
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.no_change_count == 1
        assert result.diff_items[0].action == "no_change"

    def test_unknown_position_name_creates_error_row(self) -> None:
        """未登録の役職名はエラー行として表示される."""
        session = _make_session_mock()
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "役職名": "未登録役職"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.error_count == 1
        assert result.has_errors is True
        assert any("未登録役職" in e for e in result.error_rows[0].errors)

    def test_invalid_date_creates_error_row(self) -> None:
        """不正な日付はエラー行として表示される."""
        session = _make_session_mock()
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "生年月日": "invalid"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.error_count == 1
        assert any("生年月日" in e for e in result.error_rows[0].errors)

    def test_unknown_department_name_creates_error_row(self) -> None:
        """未登録の課名はエラー行として表示される."""
        session = _make_session_mock()
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "課名": "存在しない課"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.error_count == 1
        assert any("存在しない課" in e for e in result.error_rows[0].errors)

    def test_missing_employee_code_creates_error_row(self) -> None:
        """職員番号が空の場合はエラー行として表示される."""
        session = _make_session_mock()
        raw_rows = [{"職員番号": "", "氏名": "田中 太郎"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.error_count == 1


# ---------------------------------------------------------------------------
# execute_upload
# ---------------------------------------------------------------------------


class TestExecuteUpload:
    """execute_upload の単体テスト."""

    def test_creates_new_worker(self) -> None:
        """新規Workerが正しく作成される."""
        dept = _make_dept()
        session = MagicMock()

        # マスタフェッチ + 既存Worker取得のmock（6回のexec呼び出し）
        results = [[], [], [dept], [], [], []]  # positions, branches, depts, skill_ranks, employment_types, workers

        def make_r(data: list) -> MagicMock:
            r = MagicMock()
            r.all.return_value = list(data)
            return r

        session.exec.side_effect = [make_r(d) for d in results]

        captured_workers: list[Worker] = []

        def _add(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.id = WORKER_ID_1  # type: ignore[assignment]
                captured_workers.append(obj)

        session.add.side_effect = _add

        def _refresh(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.id = WORKER_ID_1  # type: ignore[assignment]
                obj.tenant_id = TENANT_ID  # type: ignore[assignment]
                obj.is_special = False  # type: ignore[assignment]
                if obj.skill_rank_id is None:
                    obj.skill_rank_id = SR_ID_1  # type: ignore[assignment]
                obj.created_at = datetime(2026, 1, 1)  # type: ignore[assignment]
                obj.updated_at = datetime(2026, 1, 1)  # type: ignore[assignment]

        session.refresh.side_effect = _refresh

        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "課名": "1課"}]

        result = worker_upload_service.execute_upload(session, TENANT_ID, raw_rows)

        assert isinstance(result, WorkerUploadUpsertResponse)
        assert result.created == 1
        assert result.updated == 0

    def test_updates_existing_worker(self) -> None:
        """既存Workerが正しく更新される."""
        dept = _make_dept()
        existing = _make_worker(name="旧名前")
        session = MagicMock()

        results = [[], [], [dept], [], [], [existing]]  # positions, branches, depts, skill_ranks, employment_types, workers

        def make_r(data: list) -> MagicMock:
            r = MagicMock()
            r.all.return_value = list(data)
            return r

        session.exec.side_effect = [make_r(d) for d in results]

        def _refresh(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.created_at = datetime(2026, 1, 1)  # type: ignore[assignment]
                obj.updated_at = datetime(2026, 1, 2)  # type: ignore[assignment]

        session.refresh.side_effect = _refresh

        raw_rows = [{"職員番号": "E001", "氏名": "新名前", "課名": "1課"}]

        result = worker_upload_service.execute_upload(session, TENANT_ID, raw_rows)

        assert result.created == 0
        assert result.updated == 1
        assert existing.name == "新名前"

    def test_error_rows_raise_422(self) -> None:
        """バリデーションエラーがある場合、422例外を送出する."""
        session = MagicMock()

        results = [[], [], [], [], [], []]  # 6 items: positions, branches, depts, skill_ranks, employment_types, workers

        def make_r(data: list) -> MagicMock:
            r = MagicMock()
            r.all.return_value = list(data)
            return r

        session.exec.side_effect = [make_r(d) for d in results]

        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "役職名": "未登録役職"}]

        with pytest.raises(HTTPException) as exc_info:
            worker_upload_service.execute_upload(session, TENANT_ID, raw_rows)

        assert exc_info.value.status_code == 422
        assert "未登録役職" in exc_info.value.detail

    def test_duplicate_employee_codes_raise_422(self) -> None:
        """重複する職員番号がある場合、422例外を送出する."""
        session = MagicMock()

        results = [[], [], [], [], [], []]  # 6 items

        def make_r(data: list) -> MagicMock:
            r = MagicMock()
            r.all.return_value = list(data)
            return r

        session.exec.side_effect = [make_r(d) for d in results]

        raw_rows = [
            {"職員番号": "E001", "氏名": "田中 太郎"},
            {"職員番号": "E001", "氏名": "鈴木 花子"},
        ]

        with pytest.raises(HTTPException) as exc_info:
            worker_upload_service.execute_upload(session, TENANT_ID, raw_rows)

        assert exc_info.value.status_code == 422
        assert "E001" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 雇用形態名サポート
# ---------------------------------------------------------------------------


ET_ID_1 = uuid.uuid4()


def _make_employment_type(
    et_id: uuid.UUID = ET_ID_1, name: str = "正職員"
) -> MagicMock:
    """テスト用EmploymentTypeモックを生成する."""
    et = MagicMock()
    et.id = et_id
    et.name = name
    et.tenant_id = TENANT_ID
    return et


class TestEmploymentTypeName:
    """雇用形態名の CSV サポートに関するテスト."""

    def test_preview_with_employment_type_name(self) -> None:
        """雇用形態名を指定した行はcreateアクションで表示される."""
        dept = _make_dept()
        et = _make_employment_type()
        session = _make_session_mock(departments=[dept], employment_types=[et], workers=[])
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "課名": "1課", "雇用形態名": "正職員"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.create_count == 1
        assert result.diff_items[0].after.employment_type_name == "正職員"

    def test_preview_unknown_employment_type_creates_error_row(self) -> None:
        """未登録の雇用形態名はエラー行として表示される."""
        session = _make_session_mock()
        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "雇用形態名": "未登録雇用形態"}]

        result = worker_upload_service.preview_upload(session, TENANT_ID, raw_rows)

        assert result.error_count == 1
        assert any("未登録雇用形態" in e for e in result.error_rows[0].errors)

    def test_execute_sets_employment_type_on_new_worker(self) -> None:
        """新規Worker作成時に雇用形態IDが設定される."""
        dept = _make_dept()
        et = _make_employment_type()
        session = MagicMock()
        results = [[], [], [dept], [], [et], []]  # positions, branches, depts, skill_ranks, employment_types, workers

        def make_r(data: list) -> MagicMock:
            r = MagicMock()
            r.all.return_value = list(data)
            return r

        session.exec.side_effect = [make_r(d) for d in results]

        captured_workers: list[Worker] = []

        def _add(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.id = WORKER_ID_1  # type: ignore[assignment]
                captured_workers.append(obj)

        session.add.side_effect = _add

        def _refresh(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.id = WORKER_ID_1  # type: ignore[assignment]
                obj.tenant_id = TENANT_ID  # type: ignore[assignment]
                obj.is_special = False  # type: ignore[assignment]
                if obj.skill_rank_id is None:
                    obj.skill_rank_id = SR_ID_1  # type: ignore[assignment]
                obj.created_at = datetime(2026, 1, 1)  # type: ignore[assignment]
                obj.updated_at = datetime(2026, 1, 1)  # type: ignore[assignment]

        session.refresh.side_effect = _refresh

        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "課名": "1課", "雇用形態名": "正職員"}]
        result = worker_upload_service.execute_upload(session, TENANT_ID, raw_rows)

        assert result.created == 1
        assert len(captured_workers) == 1
        assert captured_workers[0].employment_type_id == ET_ID_1

    def test_execute_updates_employment_type_on_existing_worker(self) -> None:
        """既存Workerの雇用形態を更新できる."""
        dept = _make_dept()
        et = _make_employment_type()
        existing = _make_worker()
        existing.employment_type_id = None
        session = MagicMock()
        results = [[], [], [dept], [], [et], [existing]]

        def make_r(data: list) -> MagicMock:
            r = MagicMock()
            r.all.return_value = list(data)
            return r

        session.exec.side_effect = [make_r(d) for d in results]

        def _refresh(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.created_at = datetime(2026, 1, 1)  # type: ignore[assignment]
                obj.updated_at = datetime(2026, 1, 2)  # type: ignore[assignment]

        session.refresh.side_effect = _refresh

        raw_rows = [{"職員番号": "E001", "氏名": "田中 太郎", "課名": "1課", "雇用形態名": "正職員"}]
        result = worker_upload_service.execute_upload(session, TENANT_ID, raw_rows)

        assert result.updated == 1
        assert existing.employment_type_id == ET_ID_1
