# backend/app/models/schemas.py
"""Workerエンティティのリクエスト/レスポンスPydanticスキーマ定義."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.models import SkillRankEnum


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
