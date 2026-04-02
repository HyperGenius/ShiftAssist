# backend/tests/unit/test_shift_rules_service.py
"""shift_rules_service モジュールの単体テスト."""

from app.models.schemas import ShiftRulesConfig, ShiftRulesResponse, ShiftWarningsConfig
from app.services import shift_rules_service


class TestGetShiftRules:
    """get_shift_rules の正常系テスト."""

    def test_returns_shift_rules_response(self) -> None:
        """正常系: ShiftRulesResponse を返す."""
        result = shift_rules_service.get_shift_rules()
        assert isinstance(result, ShiftRulesResponse)

    def test_shift_rules_config_type(self) -> None:
        """正常系: shift_rules フィールドが ShiftRulesConfig 型である."""
        result = shift_rules_service.get_shift_rules()
        assert isinstance(result.shift_rules, ShiftRulesConfig)

    def test_warnings_config_type(self) -> None:
        """正常系: warnings フィールドが ShiftWarningsConfig 型である."""
        result = shift_rules_service.get_shift_rules()
        assert isinstance(result.warnings, ShiftWarningsConfig)

    def test_default_min_interval_days(self) -> None:
        """正常系: min_interval_days のデフォルト値が 10 である."""
        result = shift_rules_service.get_shift_rules()
        assert result.shift_rules.min_interval_days == 10

    def test_default_require_skill_ranks(self) -> None:
        """正常系: require_skill_ranks のデフォルト値に rank_a が含まれる."""
        result = shift_rules_service.get_shift_rules()
        assert "rank_a" in result.shift_rules.require_skill_ranks

    def test_default_allow_same_department(self) -> None:
        """正常系: allow_same_department のデフォルト値が False である."""
        result = shift_rules_service.get_shift_rules()
        assert result.shift_rules.allow_same_department is False

    def test_default_special_employment_shifts(self) -> None:
        """正常系: special_employment_shifts のデフォルト値に weekday_night が含まれる."""
        result = shift_rules_service.get_shift_rules()
        assert "weekday_night" in result.shift_rules.special_employment_shifts

    def test_default_workers_per_slot(self) -> None:
        """正常系: workers_per_slot のデフォルト値が 2 である."""
        result = shift_rules_service.get_shift_rules()
        assert result.shift_rules.workers_per_slot == 2

    def test_default_avoid_consecutive_holidays(self) -> None:
        """正常系: avoid_consecutive_holidays のデフォルト値が True である."""
        result = shift_rules_service.get_shift_rules()
        assert result.warnings.avoid_consecutive_holidays is True
