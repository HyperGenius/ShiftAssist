# backend/tests/unit/test_worker_service.py
"""worker_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.models import SkillRankEnum, Worker
from app.models.schemas import WorkerCreate, WorkerResponse, WorkerUpdate
from app.services import worker_service

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
WORKER_ID = uuid.uuid4()
DEPT_ID = uuid.uuid4()


def _make_worker(
    *,
    worker_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    name: str = "田中 太郎",
    department_id: uuid.UUID | None = None,
    skill_rank: SkillRankEnum = SkillRankEnum.rank_a,
    is_special: bool = False,
) -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = worker_id or WORKER_ID
    w.tenant_id = tenant_id
    w.name = name
    w.department_id = department_id or DEPT_ID
    w.skill_rank = skill_rank
    w.is_special = is_special
    w.created_at = datetime(2026, 1, 1)
    w.updated_at = datetime(2026, 1, 1)
    return w


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
# create_worker
# ---------------------------------------------------------------------------


class TestCreateWorker:
    """create_worker の正常系・異常系テスト."""

    def test_create_worker_success(self) -> None:
        """正常系: Departmentが存在する場合、Workerを作成して返す."""
        from app.models.models import Department

        dept = Department()
        dept.id = DEPT_ID
        dept.tenant_id = TENANT_ID

        session = MagicMock()
        exec_result_dept = MagicMock()
        exec_result_dept.first.return_value = dept

        session.exec.return_value = exec_result_dept
        session.refresh.side_effect = lambda obj: None

        data = WorkerCreate(
            name="田中 太郎",
            department_id=DEPT_ID,
            skill_rank=SkillRankEnum.rank_a,
            is_special=False,
        )

        with patch.object(
            worker_service,
            "_validate_department",
        ):
            # refreshでworkerのフィールドをセット
            def _refresh(obj: Worker) -> None:
                obj.id = WORKER_ID
                obj.tenant_id = TENANT_ID
                obj.name = "田中 太郎"
                obj.department_id = DEPT_ID
                obj.skill_rank = SkillRankEnum.rank_a
                obj.is_special = False
                obj.created_at = datetime(2026, 1, 1)
                obj.updated_at = datetime(2026, 1, 1)

            session.refresh.side_effect = _refresh

            result = worker_service.create_worker(session, TENANT_ID, data)

        assert isinstance(result, WorkerResponse)
        assert result.tenant_id == TENANT_ID
        assert result.name == "田中 太郎"
        assert result.skill_rank == SkillRankEnum.rank_a
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_create_worker_invalid_department(self) -> None:
        """異常系: Departmentが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = WorkerCreate(
            name="鈴木 花子",
            department_id=uuid.uuid4(),
            skill_rank=SkillRankEnum.rank_b,
        )

        with pytest.raises(HTTPException) as exc_info:
            worker_service.create_worker(session, TENANT_ID, data)

        assert exc_info.value.status_code == 404

    def test_create_worker_cross_tenant_department_rejected(self) -> None:
        """異常系: 他テナントのDepartment IDを指定した場合、404例外を送出する."""
        # 他テナントのDepartmentはNoneを返す（テナント条件でフィルタされる）
        session = _make_session(exec_first_return=None)
        data = WorkerCreate(
            name="山田 一郎",
            department_id=DEPT_ID,
            skill_rank=SkillRankEnum.rank_c,
        )

        with pytest.raises(HTTPException) as exc_info:
            worker_service.create_worker(session, OTHER_TENANT_ID, data)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# list_workers
# ---------------------------------------------------------------------------


class TestListWorkers:
    """list_workers の正常系テスト."""

    def test_list_workers_returns_tenant_workers(self) -> None:
        """正常系: テナントに属するWorker一覧を返す."""
        workers = [_make_worker(name="A"), _make_worker(name="B")]
        session = _make_session(exec_all_return=workers)

        result = worker_service.list_workers(session, TENANT_ID)

        assert len(result) == 2
        assert all(isinstance(r, WorkerResponse) for r in result)
        assert all(r.tenant_id == TENANT_ID for r in result)

    def test_list_workers_empty(self) -> None:
        """正常系: Workerが存在しない場合、空リストを返す."""
        session = _make_session(exec_all_return=[])

        result = worker_service.list_workers(session, TENANT_ID)

        assert result == []


# ---------------------------------------------------------------------------
# get_worker
# ---------------------------------------------------------------------------


class TestGetWorker:
    """get_worker の正常系・異常系テスト."""

    def test_get_worker_success(self) -> None:
        """正常系: Workerが存在する場合、WorkerResponseを返す."""
        worker = _make_worker()
        session = _make_session(exec_first_return=worker)

        result = worker_service.get_worker(session, TENANT_ID, WORKER_ID)

        assert result.id == WORKER_ID
        assert result.tenant_id == TENANT_ID

    def test_get_worker_not_found(self) -> None:
        """異常系: Workerが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            worker_service.get_worker(session, TENANT_ID, WORKER_ID)

        assert exc_info.value.status_code == 404

    def test_get_worker_other_tenant_returns_404(self) -> None:
        """異常系: 他テナントのWorker IDを指定した場合、404例外を送出する."""
        # 他テナントではNoneが返る
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            worker_service.get_worker(session, OTHER_TENANT_ID, WORKER_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# update_worker
# ---------------------------------------------------------------------------


class TestUpdateWorker:
    """update_worker の正常系・異常系テスト."""

    def test_update_worker_name_only(self) -> None:
        """正常系: name のみ指定した場合、該当フィールドのみ更新する."""
        worker = _make_worker()
        session = _make_session(exec_first_return=worker)
        session.refresh.side_effect = lambda obj: None

        data = WorkerUpdate(name="更新 太郎")

        with patch.object(worker_service, "_validate_department"):
            result = worker_service.update_worker(session, TENANT_ID, WORKER_ID, data)

        assert result.name == "更新 太郎"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_update_worker_with_department_validates(self) -> None:
        """正常系: department_id を含む更新時に _validate_department が呼ばれる."""
        worker = _make_worker()
        session = _make_session(exec_first_return=worker)
        session.refresh.side_effect = lambda obj: None

        new_dept_id = uuid.uuid4()
        data = WorkerUpdate(department_id=new_dept_id)

        with patch.object(worker_service, "_validate_department") as mock_validate:
            worker_service.update_worker(session, TENANT_ID, WORKER_ID, data)

        mock_validate.assert_called_once_with(session, TENANT_ID, new_dept_id)

    def test_update_worker_not_found(self) -> None:
        """異常系: Workerが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = WorkerUpdate(name="新名前")

        with pytest.raises(HTTPException) as exc_info:
            worker_service.update_worker(session, TENANT_ID, WORKER_ID, data)

        assert exc_info.value.status_code == 404

    def test_update_worker_invalid_department(self) -> None:
        """異常系: 更新時に存在しないDepartment IDを指定した場合、404例外を送出する."""
        worker = _make_worker()
        session = _make_session(exec_first_return=worker)

        data = WorkerUpdate(department_id=uuid.uuid4())

        with patch.object(
            worker_service,
            "_validate_department",
            side_effect=HTTPException(status_code=404, detail="Department not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                worker_service.update_worker(session, TENANT_ID, WORKER_ID, data)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_worker
# ---------------------------------------------------------------------------


class TestDeleteWorker:
    """delete_worker の正常系・異常系テスト."""

    def test_delete_worker_success(self) -> None:
        """正常系: Workerが存在する場合、物理削除を実行する."""
        worker = _make_worker()
        session = _make_session(exec_first_return=worker)

        worker_service.delete_worker(session, TENANT_ID, WORKER_ID)

        session.delete.assert_called_once_with(worker)
        session.commit.assert_called_once()

    def test_delete_worker_not_found(self) -> None:
        """異常系: Workerが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            worker_service.delete_worker(session, TENANT_ID, WORKER_ID)

        assert exc_info.value.status_code == 404

    def test_delete_worker_other_tenant_rejected(self) -> None:
        """異常系: 他テナントのWorkerを削除しようとした場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            worker_service.delete_worker(session, OTHER_TENANT_ID, WORKER_ID)

        assert exc_info.value.status_code == 404
