# backend/tests/unit/test_custom_rule_service.py
"""custom_rule_service モジュールの単体テスト.

外部依存（DB）は ``unittest.mock`` でMock化する。
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from app.models.models import CustomRule
from app.models.schemas import CustomRuleCreate, CustomRuleResponse, CustomRuleUpdate
from app.services import custom_rule_service
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# テスト用定数
# ---------------------------------------------------------------------------

TENANT_ID = "org_test_tenant"
OTHER_TENANT_ID = "org_other_tenant"
RULE_ID = uuid.uuid4()


def _make_custom_rule(
    *,
    rule_id: uuid.UUID | None = None,
    tenant_id: str = TENANT_ID,
    name: str = "テストルール",
    allowed_slot_types: list[str] | None = None,
    annual_limit_overrides: dict | None = None,
) -> CustomRule:
    """テスト用CustomRuleオブジェクトを生成するヘルパー."""
    r = CustomRule()
    r.id = rule_id or RULE_ID
    r.tenant_id = tenant_id
    r.name = name
    r.allowed_slot_types = allowed_slot_types
    r.annual_limit_overrides = annual_limit_overrides
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
# list_custom_rules
# ---------------------------------------------------------------------------


class TestListCustomRules:
    """list_custom_rules のテスト."""

    def test_returns_custom_rules_for_tenant(self) -> None:
        """テナントに属するカスタムルール一覧を返す."""
        rule1 = _make_custom_rule(name="ルールA")
        rule2 = _make_custom_rule(name="ルールB", rule_id=uuid.uuid4())
        session = _make_session(exec_all_return=[rule1, rule2])

        result = custom_rule_service.list_custom_rules(session, TENANT_ID)

        assert len(result) == 2
        assert result[0].name == "ルールA"
        assert result[1].name == "ルールB"

    def test_returns_empty_list_when_no_rules(self) -> None:
        """カスタムルールが存在しない場合は空リストを返す."""
        session = _make_session(exec_all_return=[])

        result = custom_rule_service.list_custom_rules(session, TENANT_ID)

        assert result == []


# ---------------------------------------------------------------------------
# get_custom_rule
# ---------------------------------------------------------------------------


class TestGetCustomRule:
    """get_custom_rule のテスト."""

    def test_returns_rule_when_found(self) -> None:
        """ルールが存在する場合はレスポンスモデルを返す."""
        rule = _make_custom_rule()
        session = _make_session(exec_first_return=rule)

        result = custom_rule_service.get_custom_rule(session, TENANT_ID, RULE_ID)

        assert result.id == RULE_ID
        assert result.name == "テストルール"

    def test_raises_404_when_not_found(self) -> None:
        """ルールが存在しない場合は HTTP 404 を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            custom_rule_service.get_custom_rule(session, TENANT_ID, RULE_ID)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# create_custom_rule
# ---------------------------------------------------------------------------


class TestCreateCustomRule:
    """create_custom_rule のテスト."""

    def test_creates_rule_successfully(self) -> None:
        """新しいカスタムルールを作成できる."""
        session = _make_session(exec_first_return=None)
        # session.refresh が呼ばれたあとにルールオブジェクトを返すようにする
        created_rule = _make_custom_rule(name="新ルール", allowed_slot_types=["sun_hol_day"])

        def mock_refresh(obj: object) -> None:
            obj.__dict__.update(created_rule.__dict__)

        session.refresh.side_effect = mock_refresh
        data = CustomRuleCreate(name="新ルール", allowed_slot_types=["sun_hol_day"])

        result = custom_rule_service.create_custom_rule(session, TENANT_ID, data)

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result.name == "新ルール"

    def test_raises_409_when_name_duplicated(self) -> None:
        """同一テナント内でルール名が重複する場合は HTTP 409 を送出する."""
        existing_rule = _make_custom_rule(name="既存ルール")
        session = _make_session(exec_first_return=existing_rule)
        data = CustomRuleCreate(name="既存ルール")

        with pytest.raises(HTTPException) as exc_info:
            custom_rule_service.create_custom_rule(session, TENANT_ID, data)

        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# update_custom_rule
# ---------------------------------------------------------------------------


class TestUpdateCustomRule:
    """update_custom_rule のテスト."""

    def test_updates_rule_successfully(self) -> None:
        """存在するルールを更新できる."""
        existing_rule = _make_custom_rule(name="旧名前")
        session = MagicMock()
        # 1回目（ルール検索）は existing_rule を返し、2回目（名前重複チェック）はNoneを返す
        first_exec = MagicMock()
        first_exec.first.return_value = existing_rule
        second_exec = MagicMock()
        second_exec.first.return_value = None
        session.exec.side_effect = [first_exec, second_exec]

        updated_rule = _make_custom_rule(name="新名前")

        def mock_refresh(obj: object) -> None:
            obj.__dict__.update(updated_rule.__dict__)

        session.refresh.side_effect = mock_refresh
        data = CustomRuleUpdate(name="新名前")

        result = custom_rule_service.update_custom_rule(session, TENANT_ID, RULE_ID, data)

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result.name == "新名前"

    def test_raises_404_when_not_found(self) -> None:
        """ルールが存在しない場合は HTTP 404 を送出する."""
        session = _make_session(exec_first_return=None)
        data = CustomRuleUpdate(name="新名前")

        with pytest.raises(HTTPException) as exc_info:
            custom_rule_service.update_custom_rule(session, TENANT_ID, RULE_ID, data)

        assert exc_info.value.status_code == 404

    def test_raises_409_when_new_name_duplicated(self) -> None:
        """変更後の名前が既存ルールと重複する場合は HTTP 409 を送出する."""
        existing_rule = _make_custom_rule(name="旧名前")
        duplicate_rule = _make_custom_rule(name="重複名前", rule_id=uuid.uuid4())
        session = MagicMock()
        first_exec = MagicMock()
        first_exec.first.return_value = existing_rule
        second_exec = MagicMock()
        second_exec.first.return_value = duplicate_rule
        session.exec.side_effect = [first_exec, second_exec]
        data = CustomRuleUpdate(name="重複名前")

        with pytest.raises(HTTPException) as exc_info:
            custom_rule_service.update_custom_rule(session, TENANT_ID, RULE_ID, data)

        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# delete_custom_rule
# ---------------------------------------------------------------------------


class TestDeleteCustomRule:
    """delete_custom_rule のテスト."""

    def test_deletes_rule_successfully(self) -> None:
        """存在するルールを削除できる."""
        rule = _make_custom_rule()
        session = _make_session(exec_first_return=rule)

        custom_rule_service.delete_custom_rule(session, TENANT_ID, RULE_ID)

        session.delete.assert_called_once_with(rule)
        session.commit.assert_called_once()

    def test_raises_404_when_not_found(self) -> None:
        """ルールが存在しない場合は HTTP 404 を送出する."""
        session = _make_session(exec_first_return=None)

        with pytest.raises(HTTPException) as exc_info:
            custom_rule_service.delete_custom_rule(session, TENANT_ID, RULE_ID)

        assert exc_info.value.status_code == 404
