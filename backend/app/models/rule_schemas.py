# backend/app/models/rule_schemas.py
"""シフトルール定義・バリデーション違反に関するPydanticスキーマ定義."""

from pydantic import BaseModel


class ShiftRulesConfig(BaseModel):
    """シフトルール設定スキーマ.

    バックエンドで一元管理されるシフト作成ルールのパラメータ定義。
    フロントエンドはこの設定を取得してリアルタイム検証に使用する。
    """

    min_interval_days: int = 10
    """最小勤務間隔（日数）。同一ワーカーの連続シフト間に必要な最低日数。"""

    require_skill_ranks: list[str] = ["rank_a"]
    """ペアに必須のスキルランク一覧。"""

    allow_same_department: bool = False
    """同一所属課ペアを許可するか。"""

    special_employment_shifts: list[str] = ["weekday_night"]
    """特別雇用者が参加できるシフト種別一覧。"""

    workers_per_slot: int = 2
    """1スロットあたりの必要人数。"""


class ShiftWarningsConfig(BaseModel):
    """シフト警告設定スキーマ.

    エラーではなく警告として扱うルールの設定。
    """

    avoid_consecutive_holidays: bool = True
    """休日の連続アサインを警告するか。"""


class ShiftRulesResponse(BaseModel):
    """ルール定義APIレスポンススキーマ."""

    shift_rules: ShiftRulesConfig
    warnings: ShiftWarningsConfig


class ValidationViolationItem(BaseModel):
    """バリデーション違反の個別アイテムスキーマ."""

    code: str
    """違反コード（例: WORK_INTERVAL, SKILL_RANK_A）。"""

    severity: str
    """重大度（"error" または "warning"）。"""

    message: str
    """ユーザー向けの違反説明メッセージ。"""

    worker_ids: list[str]
    """違反に関連するワーカーIDリスト。"""
