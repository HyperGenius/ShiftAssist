# backend/tests/unit/test_position_service.py
"""position_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.models import Position, Worker
from app.models.schemas import (
    PositionCreate,
    PositionResponse,
    PositionUpdate,
)
from app.services import position_service

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
POSITION_ID = uuid.uuid4()


def _make_position(
    *,
    position_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    name: str = "係長",
    is_excluded_from_gw: bool = False,
    is_excluded_from_sw: bool = False,
    is_excluded_from_year_end: bool = False,
    is_excluded_from_all_shifts: bool = False,
) -> Position:
    """テスト用Positionオブジェクトを生成するヘルパー."""
    p = Position()
    p.id = position_id or POSITION_ID
    p.tenant_id = tenant_id
    p.name = name
    p.is_excluded_from_gw = is_excluded_from_gw
    p.is_excluded_from_sw = is_excluded_from_sw
    p.is_excluded_from_year_end = is_excluded_from_year_end
    p.is_excluded_from_all_shifts = is_excluded_from_all_shifts
    p.created_at = datetime(2026, 1, 1)
    return p


def _make_worker() -> Worker:
    """テスト用Workerオブジェクトを生成するヘルパー."""
    w = Worker()
    w.id = uuid.uuid4()
    w.tenant_id = TENANT_ID
    w.name = "テストワーカー"
    w.position_id = POSITION_ID
    return w


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
# create_position
# ---------------------------------------------------------------------------


class TestCreatePosition:
    """create_position の正常系テスト."""

    def test_create_position_success(self) -> None:
        """正常系: Positionを作成して返す."""
        session = MagicMock()

        def _refresh(obj: Position) -> None:
            obj.id = POSITION_ID
            obj.tenant_id = TENANT_ID
            obj.name = "係長"
            obj.is_excluded_from_gw = True
            obj.is_excluded_from_sw = False
            obj.is_excluded_from_year_end = False
            obj.is_excluded_from_all_shifts = False
            obj.created_at = datetime(2026, 1, 1)

        session.refresh.side_effect = _refresh

        data = PositionCreate(
            name="係長",
            is_excluded_from_gw=True,
            is_excluded_from_sw=False,
            is_excluded_from_year_end=False,
            is_excluded_from_all_shifts=False,
        )

        result = position_service.create_position(session, TENANT_ID, data)

        assert isinstance(result, PositionResponse)
        assert result.name == "係長"
        assert result.is_excluded_from_gw is True
        session.add.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# list_positions
# ---------------------------------------------------------------------------


class TestListPositions:
    """list_positions の正常系テスト."""

    def test_list_positions_returns_tenant_positions(self) -> None:
        """正常系: テナントに属するPosition一覧を返す."""
        positions = [
            _make_position(name="係長"),
            _make_position(name="主任", is_excluded_from_gw=True),
        ]
        session = _make_session(exec_all_return=positions)

        result = position_service.list_positions(session, TENANT_ID)

        assert len(result) == 2
        assert all(isinstance(r, PositionResponse) for r in result)

    def test_list_positions_empty(self) -> None:
        """正常系: Positionが存在しない場合、空リストを返す."""
        session = _make_session(exec_all_return=[])

        result = position_service.list_positions(session, TENANT_ID)

        assert result == []


# ---------------------------------------------------------------------------
# get_position
# ---------------------------------------------------------------------------


class TestGetPosition:
    """get_position の正常系・異常系テスト."""

    def test_get_position_success(self) -> None:
        """正常系: Positionが存在する場合、PositionResponseを返す."""
        position = _make_position()
        session = _make_session(exec_first_return=position)

        result = position_service.get_position(session, TENANT_ID, POSITION_ID)

        assert result.id == POSITION_ID
        assert result.tenant_id == TENANT_ID

    def test_get_position_not_found(self) -> None:
        """異常系: Positionが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            position_service.get_position(session, TENANT_ID, POSITION_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# update_position
# ---------------------------------------------------------------------------


class TestUpdatePosition:
    """update_position の正常系・異常系テスト."""

    def test_update_position_success(self) -> None:
        """正常系: Positionを更新して返す."""
        position = _make_position()
        session = _make_session(exec_first_return=position)
        session.refresh.side_effect = lambda obj: None

        data = PositionUpdate(name="主任", is_excluded_from_gw=True)

        result = position_service.update_position(
            session, TENANT_ID, POSITION_ID, data
        )

        assert result.name == "主任"
        assert result.is_excluded_from_gw is True
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_update_position_not_found(self) -> None:
        """異常系: Positionが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = PositionUpdate(name="新名前")

        with pytest.raises(HTTPException) as exc_info:
            position_service.update_position(
                session, TENANT_ID, POSITION_ID, data
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_position
# ---------------------------------------------------------------------------


class TestDeletePosition:
    """delete_position の正常系・異常系テスト."""

    def test_delete_position_success(self) -> None:
        """正常系: Positionが存在しWorker紐づきがない場合、物理削除を実行する."""
        position = _make_position()
        session = MagicMock()

        exec_result_position = MagicMock()
        exec_result_position.first.return_value = position

        exec_result_worker = MagicMock()
        exec_result_worker.first.return_value = None

        session.exec.side_effect = [exec_result_position, exec_result_worker]

        position_service.delete_position(session, TENANT_ID, POSITION_ID)

        session.delete.assert_called_once_with(position)
        session.commit.assert_called_once()

    def test_delete_position_not_found(self) -> None:
        """異常系: Positionが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            position_service.delete_position(session, TENANT_ID, POSITION_ID)

        assert exc_info.value.status_code == 404

    def test_delete_position_blocked_by_worker(self) -> None:
        """異常系: WorkerがPositionを参照している場合、400例外を送出する."""
        position = _make_position()
        worker = _make_worker()
        session = MagicMock()

        exec_result_position = MagicMock()
        exec_result_position.first.return_value = position

        exec_result_worker = MagicMock()
        exec_result_worker.first.return_value = worker

        session.exec.side_effect = [exec_result_position, exec_result_worker]

        with pytest.raises(HTTPException) as exc_info:
            position_service.delete_position(session, TENANT_ID, POSITION_ID)

        assert exc_info.value.status_code == 400
        session.delete.assert_not_called()
