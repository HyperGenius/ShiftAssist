# backend/app/models/schemas.py
"""WorkerおよびDepartmentエンティティのリクエスト/レスポンスPydanticスキーマ定義."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from app.models.models import (
    LongHolidayTypeEnum,
    PlanStatusEnum,
    SlotTypeEnum,
    TransferTypeEnum,
)
from app.models.rule_schemas import EmploymentTypeRuleConfig


class BranchCreate(BaseModel):
    """Branch作成リクエストスキーマ."""

    name: str
    code: str


class BranchUpdate(BaseModel):
    """Branch更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    code: str | None = None


class BranchResponse(BaseModel):
    """Branchレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    code: str
    created_at: datetime


class PositionCreate(BaseModel):
    """Position作成リクエストスキーマ."""

    name: str
    is_excluded_from_gw: bool = False
    is_excluded_from_sw: bool = False
    is_excluded_from_year_end: bool = False
    is_excluded_from_all_shifts: bool = False


class PositionUpdate(BaseModel):
    """Position更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    is_excluded_from_gw: bool | None = None
    is_excluded_from_sw: bool | None = None
    is_excluded_from_year_end: bool | None = None
    is_excluded_from_all_shifts: bool | None = None


class PositionResponse(BaseModel):
    """Positionレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    is_excluded_from_gw: bool
    is_excluded_from_sw: bool
    is_excluded_from_year_end: bool
    is_excluded_from_all_shifts: bool
    created_at: datetime


class LongHolidayPeriodCreate(BaseModel):
    """LongHolidayPeriod作成リクエストスキーマ."""

    holiday_type: LongHolidayTypeEnum
    year: int
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def end_date_must_be_after_start_date(cls, v: date, info: ValidationInfo) -> date:
        """終了日は開始日以降でなければならない."""
        if "start_date" in (info.data or {}):
            if v < info.data["start_date"]:
                raise ValueError("end_date must be on or after start_date")
        return v


class LongHolidayPeriodUpdate(BaseModel):
    """LongHolidayPeriod更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    start_date: date | None = None
    end_date: date | None = None


class LongHolidayPeriodResponse(BaseModel):
    """LongHolidayPeriodレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    holiday_type: LongHolidayTypeEnum
    year: int
    start_date: date
    end_date: date
    created_at: datetime
    updated_at: datetime


class DepartmentCreate(BaseModel):
    """Department作成リクエストスキーマ."""

    name: str
    code: str
    branch_id: uuid.UUID | None = None


class DepartmentUpdate(BaseModel):
    """Department更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    code: str | None = None
    branch_id: uuid.UUID | None = None


class DepartmentResponse(BaseModel):
    """Departmentレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    code: str
    branch_id: uuid.UUID | None = None
    created_at: datetime
    deleted_at: datetime | None = None


class DepartmentListResponse(BaseModel):
    """Departmentページネーション付き一覧レスポンススキーマ."""

    total: int
    items: list[DepartmentResponse]


class DepartmentBulkItem(BaseModel):
    """バルク登録・更新の1件分のリクエストスキーマ."""

    name: str
    code: str


class DepartmentBulkRequest(BaseModel):
    """Department一括登録・更新リクエストスキーマ."""

    departments: list[DepartmentBulkItem]


class DepartmentBulkPreviewItem(BaseModel):
    """バルク処理プレビューの1件分スキーマ."""

    code: str
    name: str
    action: str  # "create" | "update" | "reactivate" | "no_change"
    old_name: str | None = None


class DepartmentBulkPreviewResponse(BaseModel):
    """Department一括登録・更新プレビューレスポンススキーマ."""

    preview: list[DepartmentBulkPreviewItem]
    create_count: int
    update_count: int
    reactivate_count: int
    no_change_count: int = 0


class DepartmentBulkUpsertResponse(BaseModel):
    """Department一括登録・更新実行結果レスポンススキーマ."""

    created: int
    updated: int
    reactivated: int
    items: list[DepartmentResponse]


class TenantSkillRankCreate(BaseModel):
    """TenantSkillRank作成リクエストスキーマ."""

    name: str
    sort_order: int = 0
    is_leader_eligible: bool = False


class TenantSkillRankUpdate(BaseModel):
    """TenantSkillRank更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    sort_order: int | None = None
    is_leader_eligible: bool | None = None


class TenantSkillRankResponse(BaseModel):
    """TenantSkillRankレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    sort_order: int
    is_leader_eligible: bool
    created_at: datetime


class EmploymentTypeCreate(BaseModel):
    """EmploymentType作成リクエストスキーマ."""

    name: str
    is_default: bool = False


class EmploymentTypeUpdate(BaseModel):
    """EmploymentType更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    is_default: bool | None = None


class EmploymentTypeResponse(BaseModel):
    """EmploymentTypeレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
    rule: EmploymentTypeRuleConfig | None = None


class EmploymentTypeRuleUpdate(BaseModel):
    """EmploymentTypeRule更新（upsert）リクエストスキーマ."""

    require_default_pair: bool = False
    allowed_slot_types: list[str] | None = None
    annual_limit_overrides: dict | None = None


class CustomRuleCreate(BaseModel):
    """CustomRule作成リクエストスキーマ."""

    name: str
    allowed_slot_types: list[str] | None = None
    annual_limit_overrides: dict | None = None
    is_assign_prohibited: bool = False


class CustomRuleUpdate(BaseModel):
    """CustomRule更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    allowed_slot_types: list[str] | None = None
    annual_limit_overrides: dict | None = None
    is_assign_prohibited: bool | None = None


class CustomRuleResponse(BaseModel):
    """CustomRuleレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    allowed_slot_types: list[str] | None = None
    annual_limit_overrides: dict | None = None
    is_assign_prohibited: bool = False
    created_at: datetime
    updated_at: datetime


class WorkerCreate(BaseModel):
    """Worker作成リクエストスキーマ."""

    employee_no: str | None = None
    employee_code: str | None = None
    name: str
    department_id: uuid.UUID
    skill_rank_id: uuid.UUID
    position_id: uuid.UUID | None = None
    employment_type_id: uuid.UUID | None = None
    custom_rule_id: uuid.UUID | None = None
    birth_date: date | None = None
    skill_acquired_at: date | None = None
    transfer_type: TransferTypeEnum | None = None
    transfer_scheduled_month: str | None = None
    is_cross_division_transfer: bool | None = None
    joined_at: date | None = None
    transferred_at: date | None = None


class WorkerUpdate(BaseModel):
    """Worker更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    employee_no: str | None = None
    employee_code: str | None = None
    name: str | None = None
    department_id: uuid.UUID | None = None
    skill_rank_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    employment_type_id: uuid.UUID | None = None
    custom_rule_id: uuid.UUID | None = None
    birth_date: date | None = None
    skill_acquired_at: date | None = None
    transfer_type: TransferTypeEnum | None = None
    transfer_scheduled_month: str | None = None
    is_cross_division_transfer: bool | None = None
    joined_at: date | None = None
    transferred_at: date | None = None


class WorkerResponse(BaseModel):
    """Workerレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    employee_no: str | None = None
    employee_code: str | None = None
    name: str
    department_id: uuid.UUID
    skill_rank_id: uuid.UUID | None = None
    position_id: uuid.UUID | None = None
    employment_type_id: uuid.UUID | None = None
    custom_rule_id: uuid.UUID | None = None
    is_special: bool | None = None  # 非推奨。後方互換性のため残存。
    birth_date: date | None = None
    skill_acquired_at: date | None = None
    transfer_type: TransferTypeEnum | None = None
    transfer_scheduled_month: str | None = None
    is_cross_division_transfer: bool | None = None
    joined_at: date | None = None
    transferred_at: date | None = None
    created_at: datetime
    updated_at: datetime


class WorkerBulkItem(BaseModel):
    """Worker一括登録・更新の1件分のリクエストスキーマ."""

    employee_no: str
    name: str
    department_code: str
    department_name: str | None = None
    skill_rank_id: uuid.UUID
    employment_type_name: str | None = None
    joined_at: date | None = None


class WorkerBulkRequest(BaseModel):
    """Worker一括登録・更新リクエストスキーマ."""

    workers: list[WorkerBulkItem]


class WorkerBulkPreviewItem(BaseModel):
    """Worker一括処理プレビューの1件分スキーマ."""

    employee_no: str
    name: str
    department_code: str
    action: str  # "create" | "update" | "no_change"
    old_name: str | None = None
    department_is_new: bool = False


class WorkerBulkPreviewResponse(BaseModel):
    """Worker一括登録・更新プレビューレスポンススキーマ."""

    preview: list[WorkerBulkPreviewItem]
    create_count: int
    update_count: int
    no_change_count: int
    new_department_count: int


class WorkerBulkUpsertResponse(BaseModel):
    """Worker一括登録・更新実行結果レスポンススキーマ."""

    created: int
    updated: int
    departments_created: int
    items: list[WorkerResponse]


class WorkerUploadRowValues(BaseModel):
    """CSV/Excelアップロード行の値スキーマ（差分比較用）."""

    name: str | None = None
    department_name: str | None = None
    position_name: str | None = None
    birth_date: str | None = None
    skill_acquired_at: str | None = None
    transfer_type: str | None = None
    transfer_scheduled_month: str | None = None
    is_cross_division_transfer: bool | None = None
    employment_type_name: str | None = None


class WorkerUploadDiffItem(BaseModel):
    """CSV/Excelアップロードの差分表示用スキーマ（1件）."""

    row_index: int
    employee_code: str
    action: str  # "create" | "update" | "no_change"
    before: WorkerUploadRowValues | None = None
    after: WorkerUploadRowValues


class WorkerUploadErrorRow(BaseModel):
    """CSV/Excelアップロードのバリデーションエラー行スキーマ."""

    row_index: int
    employee_code: str | None = None
    errors: list[str]


class WorkerUploadPreviewResponse(BaseModel):
    """CSV/ExcelアップロードのDry-run結果スキーマ."""

    diff_items: list[WorkerUploadDiffItem]
    error_rows: list[WorkerUploadErrorRow]
    create_count: int
    update_count: int
    no_change_count: int
    error_count: int
    has_errors: bool


class WorkerUploadUpsertResponse(BaseModel):
    """CSV/ExcelアップロードのUpsert実行結果スキーマ."""

    created: int
    updated: int
    items: list[WorkerResponse]


class ShiftReqCreate(BaseModel):
    """ShiftRequirement作成リクエストスキーマ."""

    department_id: uuid.UUID | None = None
    shift_date: date
    slot_type: SlotTypeEnum
    required_headcount: int

    @field_validator("required_headcount")
    @classmethod
    def headcount_must_be_positive(cls, v: int) -> int:
        """必要人数は1以上でなければならない."""
        if v < 1:
            raise ValueError("required_headcount must be at least 1")
        return v


class ShiftReqUpdate(BaseModel):
    """ShiftRequirement更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    department_id: uuid.UUID | None = None
    shift_date: date | None = None
    slot_type: SlotTypeEnum | None = None
    required_headcount: int | None = None

    @field_validator("required_headcount")
    @classmethod
    def headcount_must_be_positive(cls, v: int | None) -> int | None:
        """必要人数は1以上でなければならない."""
        if v is not None and v < 1:
            raise ValueError("required_headcount must be at least 1")
        return v


class WorkerAssignmentItem(BaseModel):
    """ShiftRequirementAssignmentの個別アイテムスキーマ."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worker_id: uuid.UUID
    is_manual_override: bool


class ShiftAssignmentsSave(BaseModel):
    """シフト要件のアサイン情報保存リクエストスキーマ.

    指定した要件に対する対応者IDリストと、強制保存フラグを受け取る。
    既存のアサイン情報はすべて置き換えられる。
    """

    worker_ids: list[uuid.UUID]
    is_manual_override: bool = False


class ShiftReqResponse(BaseModel):
    """ShiftRequirementレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    department_id: uuid.UUID | None
    shift_date: date
    slot_type: SlotTypeEnum
    required_headcount: int
    created_at: datetime
    updated_at: datetime
    assignments: list[WorkerAssignmentItem] = []


class WorkerSlotStats(BaseModel):
    """ワーカーの枠種別ごとの勤務実績スキーマ."""

    slot_type: SlotTypeEnum
    count: int
    monthly_avg: float


class WorkerStatsResponse(BaseModel):
    """個別ワーカーの統計レスポンススキーマ."""

    worker_id: uuid.UUID
    worker_name: str
    effective_months: float
    slot_stats: list[WorkerSlotStats]
    holiday_slot_monthly_avg: float


class TenantWorkerStatsResponse(BaseModel):
    """テナント全ワーカーの統計一括取得レスポンススキーマ."""

    stats_period_months: int
    items: list[WorkerStatsResponse]


class TenantStatsConfigResponse(BaseModel):
    """テナント統計設定レスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    stats_period_months: int


class TenantStatsConfigUpdate(BaseModel):
    """テナント統計設定更新リクエストスキーマ."""

    stats_period_months: int


class TenantHolidayCreate(BaseModel):
    """TenantHoliday作成リクエストスキーマ."""

    date: date
    name: str
    is_long_holiday: bool = False


class TenantHolidayBulkCreate(BaseModel):
    """TenantHoliday一括作成リクエストスキーマ."""

    holidays: list[TenantHolidayCreate]


class TenantHolidayResponse(BaseModel):
    """TenantHolidayレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    date: date
    name: str
    is_long_holiday: bool
    created_at: datetime


class ValidationContextWorkerStats(BaseModel):
    """バリデーションコンテキスト用のワーカー実績サマリースキーマ."""

    worker_id: uuid.UUID
    sun_hol_day_this_month: int
    """当月の日曜・祝日昼間シフト回数."""
    gw_last_year: int
    """前年GWシフト参加回数."""
    year_end_last_year: int
    """前年年末年始シフト参加回数."""
    last_shift_date: date | None
    """直近のシフト日付（間隔チェック用）."""


class ValidationContextResponse(BaseModel):
    """シフト作成画面マウント時の一括バリデーションコンテキストレスポンス.

    フロントエンドがリアルタイムバリデーションに必要なデータを一括で返す。
    """

    workers: list[WorkerResponse]
    worker_stats: list[ValidationContextWorkerStats]


class ShiftPlanImportResponse(BaseModel):
    """過去シフトデータ一括インポート結果レスポンススキーマ."""

    plan_id: uuid.UUID
    """作成されたシフトプランのID."""
    target_year_month: str
    """対象年月（YYYY-MM形式）."""
    status: PlanStatusEnum
    """作成されたシフトプランのステータス."""
    slots_created: int
    """作成されたShiftSlot件数."""
    assignments_created: int
    """作成されたShiftAssignment件数."""
    skipped_worker_ids: list[str]
    """存在しない社員番号のためスキップされたワーカー識別子のリスト."""


class ShiftAssignmentDetail(BaseModel):
    """ShiftAssignment詳細スキーマ（ShiftPlanDetail内で使用）."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worker_id: uuid.UUID
    is_manual_override: bool


class ShiftSlotDetail(BaseModel):
    """ShiftSlot詳細スキーマ（ShiftPlanDetail内で使用）."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: datetime
    slot_type: SlotTypeEnum
    assignments: list[ShiftAssignmentDetail] = []


class ShiftPlanDetailResponse(BaseModel):
    """ShiftPlan詳細レスポンススキーマ（スロット・アサイン情報を含む）."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    target_year_month: str
    status: PlanStatusEnum
    updated_at: datetime | None = None
    slots: list[ShiftSlotDetail] = []


class WeekdayNightStats(BaseModel):
    """weekday_night 枠の曜日別集計スキーマ."""

    weekday: int  # 0=月, 1=火, 2=水, 3=木
    count: int
    monthly_avg: float


class AggregateWorkerSlotStats(BaseModel):
    """集計ページ用・枠種別ごとの合計・月平均スキーマ."""

    slot_type: SlotTypeEnum
    count: int
    monthly_avg: float
    weekday_stats: list[WeekdayNightStats] | None = None
    """weekday_night の場合のみ曜日別集計を保持する。"""


class AggregateWorkerStats(BaseModel):
    """集計ページ用・ワーカー1名分の統計スキーマ."""

    worker_id: uuid.UUID
    worker_name: str
    effective_months: float
    slot_stats: list[AggregateWorkerSlotStats]
    position_name: str | None = None
    """役職名。position_id に紐づく名称。"""
    department_name: str | None = None
    """所属課名。department_id に紐づく名称。"""
    skill_rank_name: str | None = None
    """スキルランク名。skill_rank_id に紐づく名称。"""
    employment_type_name: str | None = None
    """雇用形態名。employment_type_id に紐づく名称。"""
    is_non_default_employment: bool = False
    """雇用形態が非デフォルト（標準外）または is_special=True の場合 True。"""
    joined_at: date | None = None
    """着任日。有効月数バッジ表示に使用。"""
    skill_acquired_at: date | None = None
    """スキルランク取得日。有効月数バッジ表示に使用。"""


class AggregateStatsResponse(BaseModel):
    """集計ページ用・テナント全ワーカーの集計レスポンススキーマ."""

    year_month: str
    """選択年月（末月, YYYY-MM形式）。"""
    period_months: int
    """集計期間月数（常に12）。"""
    items: list[AggregateWorkerStats]


class RecalculateStatsResponse(BaseModel):
    """集計テーブル再計算結果レスポンススキーマ."""

    year_month: str
    """再計算を行った末月（YYYY-MM形式）。"""
    upserted_months: list[str]
    """Upsert を実行した年月リスト。"""


class ShiftVerifyWeekdayDelta(BaseModel):
    """Verify機能用・weekday_night 枠の曜日別 Before/After 差分スキーマ."""

    weekday: int
    """曜日（0=月, 1=火, 2=水, 3=木）。"""
    before_count: int
    """Before 期間のアサイン回数合計。"""
    before_monthly_avg: float
    """Before 期間の月平均アサイン回数。"""
    after_count: int
    """After 期間のアサイン回数合計。"""
    after_monthly_avg: float
    """After 期間の月平均アサイン回数。"""
    delta_count: int
    """差分（after_count - before_count）。"""


class ShiftVerifySlotStat(BaseModel):
    """Verify機能用・枠種別ごとの Before/After 差分スキーマ."""

    slot_type: SlotTypeEnum
    before_count: int
    """Before 期間のアサイン回数合計。"""
    before_monthly_avg: float
    """Before 期間の月平均アサイン回数。"""
    after_count: int
    """After 期間のアサイン回数合計。"""
    after_monthly_avg: float
    """After 期間の月平均アサイン回数。"""
    delta_count: int
    """差分（after_count - before_count）。"""
    is_outlier: bool
    """After の月平均が全 Worker 平均 + 1σ を超える場合 True。"""
    weekday_stats: list[ShiftVerifyWeekdayDelta] | None = None
    """weekday_night の場合のみ曜日別集計を保持する。"""


class ShiftVerifyWorkerItem(BaseModel):
    """Verify機能用・ワーカー1名分の Before/After 集計スキーマ."""

    worker_id: uuid.UUID
    worker_name: str
    position_name: str | None = None
    department_name: str | None = None
    skill_rank_name: str | None = None
    employment_type_name: str | None = None
    is_non_default_employment: bool = False
    effective_months: float
    """After 期間に対する有効在籍月数。"""
    slot_stats: list[ShiftVerifySlotStat]


class ShiftVerifyResponse(BaseModel):
    """Verify機能用・シフトプランの Before/After 集計レスポンススキーマ."""

    year_month: str
    """シフトプランの対象年月（YYYY-MM形式）。"""
    before_period: str
    """Before 期間文字列（例: "2025-06 〜 2026-05"）。"""
    after_period: str
    """After 期間文字列（例: "2025-07 〜 2026-06"）。"""
    items: list[ShiftVerifyWorkerItem]



class ShiftPlanSnapshotCreate(BaseModel):
    """ShiftPlanSnapshot作成リクエストスキーマ."""

    snapshot_data: dict
    created_by: str


class ShiftPlanSnapshotResponse(BaseModel):
    """ShiftPlanSnapshotレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shift_plan_id: uuid.UUID
    snapshot_data: dict
    created_by: str
    created_at: datetime


class ShiftPlanUpdatedAtResponse(BaseModel):
    """ShiftPlan の updated_at を返すレスポンススキーマ."""

    updated_at: datetime | None = None
