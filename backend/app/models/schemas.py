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


class EmploymentTypeUpdate(BaseModel):
    """EmploymentType更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None


class EmploymentTypeResponse(BaseModel):
    """EmploymentTypeレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
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
    is_special: bool
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
    is_special: bool = False
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

    department_id: uuid.UUID
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
    department_id: uuid.UUID
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
