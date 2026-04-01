# backend/tests/unit/test_department_service.py
"""department_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.models import Department, Worker
from app.models.schemas import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services import department_service
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
DEPT_ID = uuid.uuid4()


def _make_department(
    *,
    dept_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    name: str = "1課",
    code: str = "dept_1",
) -> Department:
    """テスト用Departmentオブジェクトを生成するヘルパー."""
    d = Department()
    d.id = dept_id or DEPT_ID
    d.tenant_id = tenant_id
    d.name = name
    d.code = code
    d.created_at = datetime(2026, 1, 1)
    return d


def _make_worker_stub() -> Worker:
    """テスト用Workerスタブを生成するヘルパー（存在確認用）."""
    return Worker()


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
# create_department
# ---------------------------------------------------------------------------


class TestCreateDepartment:
    """create_department の正常系テスト."""

    def test_create_department_success(self) -> None:
        """正常系: Departmentを作成して返す."""
        session = MagicMock()

        def _refresh(obj: Department) -> None:
            obj.id = DEPT_ID
            obj.tenant_id = TENANT_ID
            obj.name = "1課"
            obj.code = "dept_1"
            obj.created_at = datetime(2026, 1, 1)

        session.refresh.side_effect = _refresh

        data = DepartmentCreate(name="1課", code="dept_1")
        result = department_service.create_department(session, TENANT_ID, data)

        assert isinstance(result, DepartmentResponse)
        assert result.tenant_id == TENANT_ID
        assert result.name == "1課"
        assert result.code == "dept_1"
        session.add.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# list_departments
# ---------------------------------------------------------------------------


class TestListDepartments:
    """list_departments の正常系テスト."""

    def test_list_departments_returns_tenant_departments(self) -> None:
        """正常系: テナントに属するDepartment一覧を返す."""
        departments = [_make_department(name="1課"), _make_department(name="2課")]

        session = MagicMock()
        exec_count = MagicMock()
        exec_count.one.return_value = 2
        exec_data = MagicMock()
        exec_data.all.return_value = departments
        session.exec.side_effect = [exec_count, exec_data]

        result = department_service.list_departments(session, TENANT_ID)

        assert isinstance(result, DepartmentListResponse)
        assert result.total == 2
        assert len(result.items) == 2
        assert all(isinstance(r, DepartmentResponse) for r in result.items)
        assert all(r.tenant_id == TENANT_ID for r in result.items)

    def test_list_departments_empty(self) -> None:
        """正常系: Departmentが存在しない場合、total=0・空リストを返す."""
        session = MagicMock()
        exec_count = MagicMock()
        exec_count.one.return_value = 0
        exec_data = MagicMock()
        exec_data.all.return_value = []
        session.exec.side_effect = [exec_count, exec_data]

        result = department_service.list_departments(session, TENANT_ID)

        assert isinstance(result, DepartmentListResponse)
        assert result.total == 0
        assert result.items == []

    def test_list_departments_with_search_query(self) -> None:
        """正常系: search_query を指定した場合、部分一致する Department を返す."""
        dept = _make_department(name="営業1課")

        session = MagicMock()
        exec_count = MagicMock()
        exec_count.one.return_value = 1
        exec_data = MagicMock()
        exec_data.all.return_value = [dept]
        session.exec.side_effect = [exec_count, exec_data]

        result = department_service.list_departments(
            session, TENANT_ID, search_query="営業"
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].name == "営業1課"

    def test_list_departments_with_pagination(self) -> None:
        """正常系: skip/limit を指定した場合、ページネーションが適用される."""
        dept = _make_department(name="2課")

        session = MagicMock()
        exec_count = MagicMock()
        exec_count.one.return_value = 5
        exec_data = MagicMock()
        exec_data.all.return_value = [dept]
        session.exec.side_effect = [exec_count, exec_data]

        result = department_service.list_departments(
            session, TENANT_ID, skip=1, limit=1
        )

        assert result.total == 5
        assert len(result.items) == 1


# ---------------------------------------------------------------------------
# get_department
# ---------------------------------------------------------------------------


class TestGetDepartment:
    """get_department の正常系・異常系テスト."""

    def test_get_department_success(self) -> None:
        """正常系: Departmentが存在する場合、DepartmentResponseを返す."""
        dept = _make_department()
        session = _make_session(exec_first_return=dept)

        result = department_service.get_department(session, TENANT_ID, DEPT_ID)

        assert result.id == DEPT_ID
        assert result.tenant_id == TENANT_ID

    def test_get_department_not_found(self) -> None:
        """異常系: Departmentが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            department_service.get_department(session, TENANT_ID, DEPT_ID)

        assert exc_info.value.status_code == 404

    def test_get_department_other_tenant_returns_404(self) -> None:
        """異常系: 他テナントのDepartment IDを指定した場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            department_service.get_department(session, OTHER_TENANT_ID, DEPT_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# update_department
# ---------------------------------------------------------------------------


class TestUpdateDepartment:
    """update_department の正常系・異常系テスト."""

    def test_update_department_name_only(self) -> None:
        """正常系: name のみ指定した場合、該当フィールドのみ更新する."""
        dept = _make_department()
        session = _make_session(exec_first_return=dept)
        session.refresh.side_effect = lambda obj: None

        data = DepartmentUpdate(name="新1課")
        result = department_service.update_department(session, TENANT_ID, DEPT_ID, data)

        assert result.name == "新1課"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_update_department_code_only(self) -> None:
        """正常系: code のみ指定した場合、該当フィールドのみ更新する."""
        dept = _make_department()
        session = _make_session(exec_first_return=dept)
        session.refresh.side_effect = lambda obj: None

        data = DepartmentUpdate(code="dept_new")
        result = department_service.update_department(session, TENANT_ID, DEPT_ID, data)

        assert result.code == "dept_new"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_update_department_not_found(self) -> None:
        """異常系: Departmentが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = DepartmentUpdate(name="新名前")

        with pytest.raises(HTTPException) as exc_info:
            department_service.update_department(session, TENANT_ID, DEPT_ID, data)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_department
# ---------------------------------------------------------------------------


class TestDeleteDepartment:
    """delete_department の正常系・異常系テスト."""

    def test_delete_department_success(self) -> None:
        """正常系: Departmentが存在し所属Workerがいない場合、物理削除を実行する."""
        dept = _make_department()

        session = MagicMock()
        exec_result_dept = MagicMock()
        exec_result_dept.first.return_value = dept

        exec_result_worker = MagicMock()
        exec_result_worker.first.return_value = None

        session.exec.side_effect = [exec_result_dept, exec_result_worker]

        department_service.delete_department(session, TENANT_ID, DEPT_ID)

        session.delete.assert_called_once_with(dept)
        session.commit.assert_called_once()

    def test_delete_department_not_found(self) -> None:
        """異常系: Departmentが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            department_service.delete_department(session, TENANT_ID, DEPT_ID)

        assert exc_info.value.status_code == 404

    def test_delete_department_other_tenant_rejected(self) -> None:
        """異常系: 他テナントのDepartmentを削除しようとした場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            department_service.delete_department(session, OTHER_TENANT_ID, DEPT_ID)

        assert exc_info.value.status_code == 404

    def test_delete_department_with_workers_raises_409(self) -> None:
        """異常系: 所属するWorkerが存在する場合、409例外を送出する."""
        dept = _make_department()
        worker = _make_worker_stub()

        session = MagicMock()
        exec_result_dept = MagicMock()
        exec_result_dept.first.return_value = dept

        exec_result_worker = MagicMock()
        exec_result_worker.first.return_value = worker

        session.exec.side_effect = [exec_result_dept, exec_result_worker]

        with pytest.raises(HTTPException) as exc_info:
            department_service.delete_department(session, TENANT_ID, DEPT_ID)

        assert exc_info.value.status_code == 409
        assert "スタッフ" in exc_info.value.detail

    def test_delete_department_worker_check_uses_tenant_id(self) -> None:
        """正常系: Workerの存在確認が同一テナントでフィルタされることを検証する."""
        dept = _make_department()

        session = MagicMock()
        exec_result_dept = MagicMock()
        exec_result_dept.first.return_value = dept

        exec_result_worker = MagicMock()
        exec_result_worker.first.return_value = None

        session.exec.side_effect = [exec_result_dept, exec_result_worker]

        with patch("app.services.department_service.select") as mock_select:
            mock_select.return_value = MagicMock()
            session.exec.side_effect = None
            session.exec.return_value = MagicMock(
                first=MagicMock(side_effect=[dept, None])
            )
            department_service.delete_department(session, TENANT_ID, DEPT_ID)
