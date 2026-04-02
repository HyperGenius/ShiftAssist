# backend/app/services/shift_rules_service.py
"""シフトルール定義サービス層.

シフト作成に関するビジネスルールを一元管理する。
フロントエンドとバックエンドが同一のルール定義を参照することで、
検証ロジックのSingle Source of Truthを実現する。
"""

from app.models.rule_schemas import (
    ShiftRulesConfig,
    ShiftRulesResponse,
    ShiftWarningsConfig,
)

# シフトルール定義（固定値。将来的にはDBやテナント設定から取得）
_SHIFT_RULES = ShiftRulesResponse(
    shift_rules=ShiftRulesConfig(
        min_interval_days=10,
        require_skill_ranks=["rank_a"],
        allow_same_department=False,
        special_employment_shifts=["weekday_night"],
        workers_per_slot=2,
    ),
    warnings=ShiftWarningsConfig(
        avoid_consecutive_holidays=True,
    ),
)


def get_shift_rules() -> ShiftRulesResponse:
    """現在のシフトルール定義を返す.

    MVPフェーズでは固定値を返す。将来的にはテナントごとのDB設定から読み込む。

    Returns:
        シフトルール定義レスポンス。
    """
    return _SHIFT_RULES
