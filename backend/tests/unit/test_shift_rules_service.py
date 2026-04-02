# backend/tests/unit/test_shift_rules_service.py
"""shift_rules_service モジュールの単体テスト."""

from unittest.mock import MagicMock

from app.models.rule_schemas import ShiftRulesConfig, ShiftRulesResponse, ShiftWarningsConfig
from app.services import shift_rules_service

TENANT_ID = "org_test_tenant"

# テスト用ルールJSONデータ
_RULES_JSON = {
    "min_interval_days": 7,
    "require_skill_ranks": ["rank_a", "rank_b"],
    "allow_same_department": True,
    "special_employment_shifts": ["weekday_night"],
    "workers_per_slot": 3,
}
_WARNINGS_JSON = {
    "avoid_consecutive_holidays": False,
}


def _make_session_no_record() -> MagicMock:
    """テナントのルール設定がDBに存在しない場合のセッションモック."""
    session = MagicMock()
    exec_result = MagicMock()
    exec_result.first.return_value = None
    session.exec.return_value = exec_result
    return session


def _make_session_with_record() -> MagicMock:
    """テナントのルール設定がDBに存在する場合のセッションモック."""
    from app.models.models import TenantRulesConfig
    import uuid
    from datetime import datetime

    config = TenantRulesConfig()
    config.id = uuid.uuid4()
    config.tenant_id = TENANT_ID
    config.rules_json = _RULES_JSON
    config.warnings_json = _WARNINGS_JSON
    config.created_at = datetime(2026, 1, 1)
    config.updated_at = datetime(2026, 1, 1)

    session = MagicMock()
    exec_result = MagicMock()
    exec_result.first.return_value = config
    session.exec.return_value = exec_result
    return session


class TestGetShiftRules:
    """get_shift_rules の正常系テスト."""

    def test_returns_default_when_no_db_record(self) -> None:
        """正常系: DBにレコードがない場合はデフォルト値を返す."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert isinstance(result, ShiftRulesResponse)

    def test_shift_rules_config_type(self) -> None:
        """正常系: shift_rules フィールドが ShiftRulesConfig 型である."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert isinstance(result.shift_rules, ShiftRulesConfig)

    def test_warnings_config_type(self) -> None:
        """正常系: warnings フィールドが ShiftWarningsConfig 型である."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert isinstance(result.warnings, ShiftWarningsConfig)

    def test_default_min_interval_days(self) -> None:
        """正常系: デフォルトの min_interval_days が 10 である."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert result.shift_rules.min_interval_days == 10

    def test_default_require_skill_ranks(self) -> None:
        """正常系: デフォルトの require_skill_ranks に rank_a が含まれる."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert "rank_a" in result.shift_rules.require_skill_ranks

    def test_default_allow_same_department(self) -> None:
        """正常系: デフォルトの allow_same_department が False である."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert result.shift_rules.allow_same_department is False

    def test_default_special_employment_shifts(self) -> None:
        """正常系: デフォルトの special_employment_shifts に weekday_night が含まれる."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert "weekday_night" in result.shift_rules.special_employment_shifts

    def test_default_workers_per_slot(self) -> None:
        """正常系: デフォルトの workers_per_slot が 2 である."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert result.shift_rules.workers_per_slot == 2

    def test_default_avoid_consecutive_holidays(self) -> None:
        """正常系: デフォルトの avoid_consecutive_holidays が True である."""
        session = _make_session_no_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert result.warnings.avoid_consecutive_holidays is True

    def test_returns_db_record_when_exists(self) -> None:
        """正常系: DBにレコードがある場合はそのデータを返す."""
        session = _make_session_with_record()
        result = shift_rules_service.get_shift_rules(session, TENANT_ID)
        assert result.shift_rules.min_interval_days == 7
        assert result.shift_rules.workers_per_slot == 3
        assert result.shift_rules.allow_same_department is True
        assert result.warnings.avoid_consecutive_holidays is False


class TestUpdateShiftRules:
    """update_shift_rules の正常系テスト."""

    def _make_payload(self) -> ShiftRulesResponse:
        return ShiftRulesResponse(
            shift_rules=ShiftRulesConfig(
                min_interval_days=7,
                require_skill_ranks=["rank_a"],
                allow_same_department=False,
                special_employment_shifts=["weekday_night"],
                workers_per_slot=3,
            ),
            warnings=ShiftWarningsConfig(avoid_consecutive_holidays=False),
        )

    def test_create_new_record_when_none_exists(self) -> None:
        """正常系: DBにレコードがない場合は新規作成して返す."""
        from app.models.models import TenantRulesConfig
        import uuid
        from datetime import datetime

        # セッションモック: exec で None を返す（レコードなし）
        session = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = None
        session.exec.return_value = exec_result

        # refresh の副作用: configのrules_json/warnings_jsonを設定する
        payload = self._make_payload()

        def fake_refresh(obj: object) -> None:
            if isinstance(obj, TenantRulesConfig):
                obj.rules_json = payload.shift_rules.model_dump()
                obj.warnings_json = payload.warnings.model_dump()

        session.refresh.side_effect = fake_refresh

        result = shift_rules_service.update_shift_rules(session, TENANT_ID, payload)

        session.add.assert_called_once()
        session.commit.assert_called_once()
        assert result.shift_rules.min_interval_days == 7
        assert result.shift_rules.workers_per_slot == 3
        assert result.warnings.avoid_consecutive_holidays is False

    def test_update_existing_record(self) -> None:
        """正常系: DBにレコードがある場合は上書き更新して返す."""
        from app.models.models import TenantRulesConfig
        import uuid
        from datetime import datetime

        config = TenantRulesConfig()
        config.id = uuid.uuid4()
        config.tenant_id = TENANT_ID
        config.rules_json = _RULES_JSON
        config.warnings_json = _WARNINGS_JSON
        config.created_at = datetime(2026, 1, 1)
        config.updated_at = datetime(2026, 1, 1)

        session = MagicMock()
        exec_result = MagicMock()
        exec_result.first.return_value = config
        session.exec.return_value = exec_result

        payload = self._make_payload()

        def fake_refresh(obj: object) -> None:
            if isinstance(obj, TenantRulesConfig):
                obj.rules_json = payload.shift_rules.model_dump()
                obj.warnings_json = payload.warnings.model_dump()

        session.refresh.side_effect = fake_refresh

        result = shift_rules_service.update_shift_rules(session, TENANT_ID, payload)

        # add は呼ばれない（既存レコードを更新）
        session.add.assert_not_called()
        session.commit.assert_called_once()
        assert result.shift_rules.min_interval_days == 7
        assert result.shift_rules.workers_per_slot == 3
        assert result.warnings.avoid_consecutive_holidays is False
