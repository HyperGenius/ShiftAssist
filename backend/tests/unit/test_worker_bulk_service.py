# backend/tests/unit/test_worker_bulk_service.py
"""worker_service の一括登録（バルクUpsert）機能の単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.models import Department, TenantSkillRank, Worker
from app.models.schemas import WorkerBulkItem, WorkerBulkPreviewResponse, WorkerBulkUpsertResponse
from app.services import worker_service

# ---------------------------------------------------------------------------
# テスト用定数
# ---------------------------------------------------------------------------

TENANT_ID = "org_bulk_tenant"
DEPT_ID_1 = uuid.uuid4()
DEPT_ID_2 = uuid.uuid4()
SKILL_RANK_ID = uuid.uuid4()
WORKER_ID_1 = uuid.uuid4()
WORKER_ID_2 = uuid.uuid4()


def _make_department(
    *,
    dept_id: uuid.UUID | None = None,
    code: str = "dept_1",
    name: str = "1課",
    deleted_at: datetime | None = None,
) -> Department:
    """テスト用Departmentオブジェクトを生成するヘルパー."""
    d = Department()
    d.id = dept_id or DEPT_ID_1
    d.tenant_id = TENANT_ID
    d.name = name
    d.code = code
    d.created_at = datetime(2026, 1, 1)
    d.deleted_at = deleted_at
    return d


def _make_worker(
    *,
    worker_id: uuid.UUID | None = None,
    employee_no: str = "EMP001",
    name: str = "田中 太郎",
    department_id: uuid.UUID | None = None,
    skill_rank_id: uuid.UUID | None = None,
    is_special: bool = False,
) -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = worker_id or WORKER_ID_1
    w.tenant_id = TENANT_ID
    w.employee_no = employee_no
    w.name = name
    w.department_id = department_id or DEPT_ID_1
    w.skill_rank_id = skill_rank_id or SKILL_RANK_ID
    w.is_special = is_special
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


def _make_bulk_item(
    *,
    employee_no: str = "EMP001",
    name: str = "田中 太郎",
    department_code: str = "dept_1",
    department_name: str | None = None,
    skill_rank_id: uuid.UUID | None = None,
    is_special: bool = False,
) -> WorkerBulkItem:
    """テスト用WorkerBulkItemを生成するヘルパー."""
    return WorkerBulkItem(
        employee_no=employee_no,
        name=name,
        department_code=department_code,
        department_name=department_name,
        skill_rank_id=skill_rank_id or SKILL_RANK_ID,
        is_special=is_special,
    )


# ---------------------------------------------------------------------------
# _validate_no_duplicate_employee_nos
# ---------------------------------------------------------------------------


class TestValidateNoDuplicateEmployeeNos:
    """_validate_no_duplicate_employee_nos の単体テスト."""

    def test_no_duplicates_passes(self) -> None:
        """正常系: 重複がない場合は例外を送出しない."""
        items = [
            _make_bulk_item(employee_no="EMP001"),
            _make_bulk_item(employee_no="EMP002"),
            _make_bulk_item(employee_no="EMP003"),
        ]
        # 例外が発生しないことを確認
        worker_service._validate_no_duplicate_employee_nos(items)

    def test_duplicate_raises_422(self) -> None:
        """異常系: 重複するemployee_noがある場合、422例外を送出する."""
        items = [
            _make_bulk_item(employee_no="EMP001"),
            _make_bulk_item(employee_no="EMP002"),
            _make_bulk_item(employee_no="EMP001"),  # 重複
        ]
        with pytest.raises(HTTPException) as exc_info:
            worker_service._validate_no_duplicate_employee_nos(items)

        assert exc_info.value.status_code == 422
        assert "EMP001" in exc_info.value.detail


# ---------------------------------------------------------------------------
# _ensure_departments
# ---------------------------------------------------------------------------


class TestEnsureDepartments:
    """_ensure_departments の単体テスト."""

    def test_existing_department_resolves_id(self) -> None:
        """正常系: 既存の課コードが正しくIDにマッピングされる."""
        existing_dept = _make_department(dept_id=DEPT_ID_1, code="dept_1")
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = [existing_dept]
        session.exec.return_value = exec_result

        items = [_make_bulk_item(department_code="dept_1")]
        dept_id_map, created_count = worker_service._ensure_departments(
            session, TENANT_ID, items
        )

        assert dept_id_map["dept_1"] == DEPT_ID_1
        assert created_count == 0
        session.add.assert_not_called()

    def test_missing_department_auto_creates(self) -> None:
        """正常系: 未登録の課コードが自動生成される."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = []  # 既存の課なし
        session.exec.return_value = exec_result

        new_dept_id = uuid.uuid4()

        def _flush_side_effect() -> None:
            pass

        session.flush.side_effect = _flush_side_effect

        # flushした後にIDが設定されるようにsession.addのside_effectを設定
        captured_dept: list[Department] = []

        def _add_side_effect(obj: object) -> None:
            if isinstance(obj, Department):
                obj.id = new_dept_id  # type: ignore[assignment]
                captured_dept.append(obj)

        session.add.side_effect = _add_side_effect

        items = [_make_bulk_item(department_code="dept_new", department_name="新課")]
        dept_id_map, created_count = worker_service._ensure_departments(
            session, TENANT_ID, items
        )

        assert created_count == 1
        assert len(captured_dept) == 1
        assert captured_dept[0].code == "dept_new"
        assert captured_dept[0].name == "新課"
        assert captured_dept[0].tenant_id == TENANT_ID

    def test_missing_department_uses_code_as_name_when_no_name(self) -> None:
        """正常系: department_name 未指定の場合、コードを名称として使用する."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = []
        session.exec.return_value = exec_result

        captured_dept: list[Department] = []

        def _add_side_effect(obj: object) -> None:
            if isinstance(obj, Department):
                obj.id = uuid.uuid4()  # type: ignore[assignment]
                captured_dept.append(obj)

        session.add.side_effect = _add_side_effect

        items = [_make_bulk_item(department_code="dept_no_name", department_name=None)]
        worker_service._ensure_departments(session, TENANT_ID, items)

        assert len(captured_dept) == 1
        assert captured_dept[0].name == "dept_no_name"  # コードが名称として使用される

    def test_deleted_department_reactivated(self) -> None:
        """正常系: 論理削除済みの課は再活性化される."""
        deleted_dept = _make_department(
            dept_id=DEPT_ID_1, code="dept_deleted",
            deleted_at=datetime(2025, 1, 1)
        )
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = [deleted_dept]
        session.exec.return_value = exec_result

        items = [_make_bulk_item(department_code="dept_deleted")]
        dept_id_map, created_count = worker_service._ensure_departments(
            session, TENANT_ID, items
        )

        assert created_count == 0
        assert dept_id_map["dept_deleted"] == DEPT_ID_1
        assert deleted_dept.deleted_at is None  # 再活性化されている


# ---------------------------------------------------------------------------
# preview_bulk_upsert_workers
# ---------------------------------------------------------------------------


class TestPreviewBulkUpsertWorkers:
    """preview_bulk_upsert_workers の単体テスト."""

    def test_all_new_workers(self) -> None:
        """正常系: 全件新規の場合、create_countが正しく計算される."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = []  # 既存なし
        session.exec.return_value = exec_result

        items = [
            _make_bulk_item(employee_no="EMP001", name="田中 太郎"),
            _make_bulk_item(employee_no="EMP002", name="鈴木 花子"),
        ]
        result = worker_service.preview_bulk_upsert_workers(session, TENANT_ID, items)

        assert isinstance(result, WorkerBulkPreviewResponse)
        assert result.create_count == 2
        assert result.update_count == 0
        assert result.no_change_count == 0
        assert all(p.action == "create" for p in result.preview)

    def test_existing_worker_shows_update(self) -> None:
        """正常系: 既存Workerが存在する場合、updateとして検出される."""
        existing = _make_worker(employee_no="EMP001", name="旧名前")
        existing_dept = _make_department(dept_id=DEPT_ID_1, code="dept_1")

        session = MagicMock()
        # preview_bulk_upsert_workers の呼び出し順序:
        # 1. _fetch_workers_by_employee_nos -> Worker取得
        # 2. _fetch_departments_by_codes -> Department取得
        exec_workers = MagicMock()
        exec_workers.all.return_value = [existing]
        exec_depts = MagicMock()
        exec_depts.all.return_value = [existing_dept]
        session.exec.side_effect = [exec_workers, exec_depts]

        items = [_make_bulk_item(employee_no="EMP001", name="新名前", department_code="dept_1")]
        result = worker_service.preview_bulk_upsert_workers(session, TENANT_ID, items)

        assert result.create_count == 0
        assert result.update_count == 1
        assert result.preview[0].action == "update"
        assert result.preview[0].old_name == "旧名前"

    def test_new_department_flagged(self) -> None:
        """正常系: 未登録の課コードが department_is_new=True でフラグされる."""
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.all.return_value = []  # 既存部門・Workerなし
        session.exec.return_value = exec_result

        items = [_make_bulk_item(employee_no="EMP001", department_code="dept_new")]
        result = worker_service.preview_bulk_upsert_workers(session, TENANT_ID, items)

        assert result.new_department_count == 1
        assert result.preview[0].department_is_new is True

    def test_duplicate_employee_no_raises_422(self) -> None:
        """異常系: 重複するemployee_noが含まれる場合、422例外を送出する."""
        session = MagicMock()
        items = [
            _make_bulk_item(employee_no="EMP001"),
            _make_bulk_item(employee_no="EMP001"),  # 重複
        ]
        with pytest.raises(HTTPException) as exc_info:
            worker_service.preview_bulk_upsert_workers(session, TENANT_ID, items)

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# bulk_upsert_workers
# ---------------------------------------------------------------------------


class TestBulkUpsertWorkers:
    """bulk_upsert_workers の単体テスト."""

    def test_creates_new_workers(self) -> None:
        """正常系: 全件新規の場合、全Worker が作成される."""
        skill_rank = TenantSkillRank()
        skill_rank.id = SKILL_RANK_ID
        skill_rank.tenant_id = TENANT_ID
        existing_dept = _make_department(dept_id=DEPT_ID_1, code="dept_1")

        session = MagicMock()

        # exec呼び出し順序:
        # 1. _validate_skill_rank -> skill rank 存在確認
        # 2. _ensure_departments -> 課コードの取得
        # 3. _fetch_workers_by_employee_nos -> 既存Worker取得

        exec_skill = MagicMock()
        exec_skill.first.return_value = skill_rank
        exec_dept = MagicMock()
        exec_dept.all.return_value = [existing_dept]
        exec_worker = MagicMock()
        exec_worker.all.return_value = []  # 既存Workerなし

        session.exec.side_effect = [exec_skill, exec_dept, exec_worker]

        captured_workers: list[Worker] = []

        def _add_side_effect(obj: object) -> None:
            if isinstance(obj, Worker):
                obj.id = uuid.uuid4()  # type: ignore[assignment]
                captured_workers.append(obj)

        session.add.side_effect = _add_side_effect
        session.refresh.side_effect = lambda obj: None

        items = [
            _make_bulk_item(employee_no="EMP001", name="田中 太郎", department_code="dept_1"),
        ]

        with patch.object(worker_service, "_validate_skill_rank"):
            # refreshでworkerのフィールドをセット
            def _refresh(obj: Worker) -> None:
                if isinstance(obj, Worker):
                    obj.id = WORKER_ID_1
                    obj.tenant_id = TENANT_ID
                    obj.employee_no = obj.employee_no
                    obj.name = obj.name
                    obj.department_id = obj.department_id
                    obj.skill_rank_id = obj.skill_rank_id
                    obj.is_special = obj.is_special
                    obj.created_at = datetime(2026, 1, 1)
                    obj.updated_at = datetime(2026, 1, 1)

            session.refresh.side_effect = _refresh

            # _ensure_departments と _fetch_workers_by_employee_nos をモック化
            with patch.object(
                worker_service,
                "_ensure_departments",
                return_value=({"dept_1": DEPT_ID_1}, 0),
            ), patch.object(
                worker_service,
                "_fetch_workers_by_employee_nos",
                return_value={},
            ):
                result = worker_service.bulk_upsert_workers(session, TENANT_ID, items)

        assert isinstance(result, WorkerBulkUpsertResponse)
        assert result.created == 1
        assert result.updated == 0
        assert result.departments_created == 0

    def test_updates_existing_workers(self) -> None:
        """正常系: 既存Workerが存在する場合、更新される."""
        existing = _make_worker(employee_no="EMP001", name="旧名前")
        session = MagicMock()
        session.refresh.side_effect = lambda obj: None

        items = [
            _make_bulk_item(employee_no="EMP001", name="新名前", department_code="dept_1"),
        ]

        with patch.object(worker_service, "_validate_skill_rank"), patch.object(
            worker_service,
            "_ensure_departments",
            return_value=({"dept_1": DEPT_ID_1}, 0),
        ), patch.object(
            worker_service,
            "_fetch_workers_by_employee_nos",
            return_value={"EMP001": existing},
        ):
            def _refresh(obj: Worker) -> None:
                if isinstance(obj, Worker):
                    obj.created_at = datetime(2026, 1, 1)
                    obj.updated_at = datetime(2026, 1, 2)

            session.refresh.side_effect = _refresh

            result = worker_service.bulk_upsert_workers(session, TENANT_ID, items)

        assert result.created == 0
        assert result.updated == 1
        assert existing.name == "新名前"

    def test_department_auto_created(self) -> None:
        """正常系: 未登録の課が自動生成された場合、departments_createdが正しい."""
        session = MagicMock()
        session.refresh.side_effect = lambda obj: None

        items = [_make_bulk_item(employee_no="EMP001", department_code="dept_new")]

        with patch.object(worker_service, "_validate_skill_rank"), patch.object(
            worker_service,
            "_ensure_departments",
            return_value=({"dept_new": DEPT_ID_2}, 1),  # 1件自動生成
        ), patch.object(
            worker_service,
            "_fetch_workers_by_employee_nos",
            return_value={},
        ):
            def _refresh(obj: Worker) -> None:
                if isinstance(obj, Worker):
                    obj.id = WORKER_ID_1
                    obj.tenant_id = TENANT_ID
                    obj.employee_no = "EMP001"
                    obj.name = "田中 太郎"
                    obj.department_id = DEPT_ID_2
                    obj.skill_rank_id = SKILL_RANK_ID
                    obj.is_special = False
                    obj.created_at = datetime(2026, 1, 1)
                    obj.updated_at = datetime(2026, 1, 1)

            session.refresh.side_effect = _refresh
            session.add.side_effect = lambda obj: setattr(obj, "id", WORKER_ID_1) if isinstance(obj, Worker) else None

            result = worker_service.bulk_upsert_workers(session, TENANT_ID, items)

        assert result.departments_created == 1
        assert result.created == 1

    def test_duplicate_employee_no_raises_422(self) -> None:
        """異常系: 重複するemployee_noが含まれる場合、422例外を送出する."""
        session = MagicMock()
        items = [
            _make_bulk_item(employee_no="EMP001"),
            _make_bulk_item(employee_no="EMP001"),  # 重複
        ]
        with pytest.raises(HTTPException) as exc_info:
            worker_service.bulk_upsert_workers(session, TENANT_ID, items)

        assert exc_info.value.status_code == 422

    def test_invalid_skill_rank_raises_404(self) -> None:
        """異常系: 存在しないskill_rank_idが含まれる場合、404例外を送出する."""
        session = MagicMock()
        items = [_make_bulk_item(employee_no="EMP001")]

        with patch.object(
            worker_service,
            "_validate_skill_rank",
            side_effect=HTTPException(status_code=404, detail="SkillRank not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                worker_service.bulk_upsert_workers(session, TENANT_ID, items)

        assert exc_info.value.status_code == 404
