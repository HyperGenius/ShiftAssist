# backend/app/models/schemas.py
"""WorkerおよびDepartmentエンティティのリクエスト/レスポンスPydanticスキーマ定義."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.models import SkillRankEnum, SlotTypeEnum


class DepartmentCreate(BaseModel):
    """Department作成リクエストスキーマ."""

    name: str
    code: str


class DepartmentUpdate(BaseModel):
    """Department更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    code: str | None = None


class DepartmentResponse(BaseModel):
    """Departmentレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    code: str
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
    action: str  # "create" | "update" | "reactivate"
    old_name: str | None = None


class DepartmentBulkPreviewResponse(BaseModel):
    """Department一括登録・更新プレビューレスポンススキーマ."""

    preview: list[DepartmentBulkPreviewItem]
    create_count: int
    update_count: int
    reactivate_count: int


class DepartmentBulkUpsertResponse(BaseModel):
    """Department一括登録・更新実行結果レスポンススキーマ."""

    created: int
    updated: int
    reactivated: int
    items: list[DepartmentResponse]


class WorkerCreate(BaseModel):
    """Worker作成リクエストスキーマ."""

    name: str
    department_id: uuid.UUID
    skill_rank: SkillRankEnum
    is_special: bool = False


class WorkerUpdate(BaseModel):
    """Worker更新リクエストスキーマ.

    すべてのフィールドはオプショナル。指定したフィールドのみ更新される。
    """

    name: str | None = None
    department_id: uuid.UUID | None = None
    skill_rank: SkillRankEnum | None = None
    is_special: bool | None = None


class WorkerResponse(BaseModel):
    """Workerレスポンススキーマ.

    ORMモデルからの変換に対応するため ``from_attributes=True`` を設定。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: str
    name: str
    department_id: uuid.UUID
    skill_rank: SkillRankEnum
    is_special: bool
    created_at: datetime
    updated_at: datetime


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
