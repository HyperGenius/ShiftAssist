# backend/app/models/rule_schemas.py
"""シフトルール定義・バリデーション違反に関するPydanticスキーマ定義."""

from pydantic import BaseModel, field_validator


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

    target_departments: list[str] = []
    """シフト対象とする部門コードの一覧。target_all_departments が False の場合に使用。"""

    target_all_departments: bool = True
    """テナント全体（全課）を対象とするか。True の場合は target_departments の設定は無視される。"""

    hired_tenure_months: int = 6
    """採用（transfer_type=hired）のアサイン可能開始までの月数。0 を指定すると制限なし。"""

    cross_division_transfer_tenure_months: int = 3
    """事業部間転入（transfer_type=transfer_in かつ is_cross_division_transfer=True）の
    アサイン可能開始までの月数。0 を指定すると制限なし。"""

    @field_validator("hired_tenure_months", "cross_division_transfer_tenure_months")
    @classmethod
    def tenure_months_non_negative(cls, v: int) -> int:
        """在籍期間制限月数は0以上でなければならない."""
        if v < 0:
            raise ValueError("tenure_months は0以上の値を指定してください")
        return v

    @field_validator("min_interval_days")
    @classmethod
    def min_interval_days_non_negative(cls, v: int) -> int:
        """最小勤務間隔は0以上でなければならない."""
        if v < 0:
            raise ValueError("min_interval_days は0以上の値を指定してください")
        return v

    @field_validator("workers_per_slot")
    @classmethod
    def workers_per_slot_positive(cls, v: int) -> int:
        """1スロットあたりの必要人数は1以上でなければならない."""
        if v < 1:
            raise ValueError("workers_per_slot は1以上の値を指定してください")
        return v


class AnnualShiftLimitsConfig(BaseModel):
    """年間シフト回数上限設定スキーマ.

    1ワーカーあたりの年間合計に対する上限。
    0 を指定すると制限なしとして扱う。
    """

    annual_total: int = 22
    """全スロット合計の年間上限。"""

    weekday_night: int = 10
    """weekday_night の年間上限。"""

    sat_day: int = 3
    """sat_day の年間上限。"""

    sat_night: int = 3
    """sat_night の年間上限。"""

    sun_hol_day: int = 4
    """sun_hol_day の年間上限（long_hol_day の実績を合算）。"""

    sun_hol_night: int = 5
    """sun_hol_night の年間上限（long_hol_night の実績を合算）。"""

    sat_pre_hol_night: int = 4
    """sat_pre_hol_night の年間上限。"""


class ShiftWarningsConfig(BaseModel):
    """シフト警告設定スキーマ.

    エラーではなく警告として扱うルールの設定。
    """

    avoid_consecutive_holidays: bool = True
    """休日の連続アサインを警告するか。"""

    annual_shift_limits: AnnualShiftLimitsConfig = None  # type: ignore[assignment]
    """年間シフト回数上限設定。"""

    def model_post_init(self, __context: object) -> None:
        """annual_shift_limits のデフォルト値を設定する."""
        if self.annual_shift_limits is None:
            self.annual_shift_limits = AnnualShiftLimitsConfig()


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
