# backend/tests/unit/test_skill_rank_service.py
"""skill_rank_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from app.models.models import TenantSkillRank
from app.models.schemas import (
    TenantSkillRankCreate,
    TenantSkillRankResponse,
    TenantSkillRankUpdate,
)
from app.services import skill_rank_service
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
SKILL_RANK_ID = uuid.uuid4()


def _make_skill_rank(
    *,
    rank_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    name: str = "ランクA",
    sort_order: int = 0,
    is_leader_eligible: bool = True,
) -> TenantSkillRank:
    """テスト用TenantSkillRankオブジェクトを生成するヘルパー."""
    r = TenantSkillRank()
    r.id = rank_id or SKILL_RANK_ID
    r.tenant_id = tenant_id
    r.name = name
    r.sort_order = sort_order
    r.is_leader_eligible = is_leader_eligible
    r.created_at = datetime(2026, 1, 1)
    return r


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
# create_skill_rank
# ---------------------------------------------------------------------------


class TestCreateSkillRank:
    """create_skill_rank の正常系テスト."""

    def test_create_skill_rank_success(self) -> None:
        """正常系: TenantSkillRankを作成して返す."""
        rank = _make_skill_rank()
        session = MagicMock()
        session.refresh.side_effect = lambda obj: None

        data = TenantSkillRankCreate(
            name="ランクA",
            sort_order=0,
            is_leader_eligible=True,
        )

        def _refresh(obj: TenantSkillRank) -> None:
            obj.id = SKILL_RANK_ID
            obj.tenant_id = TENANT_ID
            obj.name = "ランクA"
            obj.sort_order = 0
            obj.is_leader_eligible = True
            obj.created_at = datetime(2026, 1, 1)

        session.refresh.side_effect = _refresh

        result = skill_rank_service.create_skill_rank(session, TENANT_ID, data)

        assert isinstance(result, TenantSkillRankResponse)
        assert result.name == "ランクA"
        assert result.is_leader_eligible is True
        session.add.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# list_skill_ranks
# ---------------------------------------------------------------------------


class TestListSkillRanks:
    """list_skill_ranks の正常系テスト."""

    def test_list_skill_ranks_returns_tenant_ranks(self) -> None:
        """正常系: テナントに属するスキルランク一覧を返す."""
        ranks = [
            _make_skill_rank(name="ランクA", sort_order=0),
            _make_skill_rank(name="ランクB", sort_order=1, is_leader_eligible=False),
        ]
        session = _make_session(exec_all_return=ranks)

        result = skill_rank_service.list_skill_ranks(session, TENANT_ID)

        assert len(result) == 2
        assert all(isinstance(r, TenantSkillRankResponse) for r in result)

    def test_list_skill_ranks_empty(self) -> None:
        """正常系: スキルランクが存在しない場合、空リストを返す."""
        session = _make_session(exec_all_return=[])

        result = skill_rank_service.list_skill_ranks(session, TENANT_ID)

        assert result == []


# ---------------------------------------------------------------------------
# get_skill_rank
# ---------------------------------------------------------------------------


class TestGetSkillRank:
    """get_skill_rank の正常系・異常系テスト."""

    def test_get_skill_rank_success(self) -> None:
        """正常系: スキルランクが存在する場合、TenantSkillRankResponseを返す."""
        rank = _make_skill_rank()
        session = _make_session(exec_first_return=rank)

        result = skill_rank_service.get_skill_rank(session, TENANT_ID, SKILL_RANK_ID)

        assert result.id == SKILL_RANK_ID
        assert result.tenant_id == TENANT_ID

    def test_get_skill_rank_not_found(self) -> None:
        """異常系: スキルランクが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            skill_rank_service.get_skill_rank(session, TENANT_ID, SKILL_RANK_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# update_skill_rank
# ---------------------------------------------------------------------------


class TestUpdateSkillRank:
    """update_skill_rank の正常系・異常系テスト."""

    def test_update_skill_rank_success(self) -> None:
        """正常系: スキルランクを更新して返す."""
        rank = _make_skill_rank()
        session = _make_session(exec_first_return=rank)
        session.refresh.side_effect = lambda obj: None

        data = TenantSkillRankUpdate(name="シニア", is_leader_eligible=False)

        result = skill_rank_service.update_skill_rank(
            session, TENANT_ID, SKILL_RANK_ID, data
        )

        assert result.name == "シニア"
        session.add.assert_called_once()
        session.commit.assert_called_once()

    def test_update_skill_rank_not_found(self) -> None:
        """異常系: スキルランクが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)
        data = TenantSkillRankUpdate(name="新名前")

        with pytest.raises(HTTPException) as exc_info:
            skill_rank_service.update_skill_rank(
                session, TENANT_ID, SKILL_RANK_ID, data
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_skill_rank
# ---------------------------------------------------------------------------


class TestDeleteSkillRank:
    """delete_skill_rank の正常系・異常系テスト."""

    def test_delete_skill_rank_success(self) -> None:
        """正常系: スキルランクが存在する場合、物理削除を実行する."""
        rank = _make_skill_rank()
        session = _make_session(exec_first_return=rank)

        skill_rank_service.delete_skill_rank(session, TENANT_ID, SKILL_RANK_ID)

        session.delete.assert_called_once_with(rank)
        session.commit.assert_called_once()

    def test_delete_skill_rank_not_found(self) -> None:
        """異常系: スキルランクが存在しない場合、404例外を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            skill_rank_service.delete_skill_rank(session, TENANT_ID, SKILL_RANK_ID)

        assert exc_info.value.status_code == 404
