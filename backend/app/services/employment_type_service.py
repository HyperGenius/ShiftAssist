# backend/app/services/employment_type_service.py
"""EmploymentType CRUDサービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import EmploymentType, EmploymentTypeRule
from app.models.rule_schemas import AnnualPartialLimitsConfig, EmploymentTypeRuleConfig
from app.models.schemas import (
    EmploymentTypeCreate,
    EmploymentTypeResponse,
    EmploymentTypeRuleUpdate,
    EmploymentTypeUpdate,
)


def _clear_default_flag(
    session: Session,
    tenant_id: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """テナント内の既存デフォルトフラグを解除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        exclude_id: 解除から除外するEmploymentTypeID（更新対象自身を除く場合に使用）。
    """
    query = select(EmploymentType).where(
        EmploymentType.tenant_id == tenant_id,
        EmploymentType.is_default.is_(True),  # type: ignore[union-attr]
    )
    if exclude_id is not None:
        query = query.where(EmploymentType.id != exclude_id)  # type: ignore[arg-type]
    existing_default = session.exec(query).first()
    if existing_default is not None:
        existing_default.is_default = False  # type: ignore[assignment]
        session.add(existing_default)


def create_employment_type(
    session: Session, tenant_id: str, data: EmploymentTypeCreate
) -> EmploymentTypeResponse:
    """新しいEmploymentTypeを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: EmploymentType作成リクエストデータ。

    Returns:
        作成されたEmploymentTypeのレスポンスモデル。

    Raises:
        HTTPException: 同テナント内で同名の雇用形態が既に存在する場合。
    """
    existing = session.exec(
        select(EmploymentType).where(
            EmploymentType.tenant_id == tenant_id,
            EmploymentType.name == data.name,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"EmploymentType '{data.name}' already exists.",
        )

    # is_default=True の場合、既存のデフォルトフラグを解除する（アトミック処理）
    if data.is_default is True:
        _clear_default_flag(session, tenant_id)

    employment_type = EmploymentType(
        tenant_id=tenant_id,
        name=data.name,
        is_default=data.is_default if data.is_default is not None else False,
    )
    session.add(employment_type)
    session.commit()
    session.refresh(employment_type)
    return _build_response(session, employment_type)


def _load_rule(
    session: Session, employment_type_id: uuid.UUID
) -> EmploymentTypeRuleConfig | None:
    """雇用形態IDに対応するルール設定を読み込む.

    Args:
        session: SQLModelセッション。
        employment_type_id: 対象の雇用形態ID。

    Returns:
        EmploymentTypeRuleConfig（ルールが設定されている場合）、または None（ルールが未設定の場合）。
        呼び出し側で None の場合のデフォルト値処理を行うこと。
    """
    rule_row = session.exec(
        select(EmploymentTypeRule).where(
            EmploymentTypeRule.employment_type_id == employment_type_id,  # type: ignore[arg-type]
        )
    ).first()
    if rule_row is None:
        return None
    overrides_raw = rule_row.annual_limit_overrides
    annual_limit_overrides = (
        AnnualPartialLimitsConfig(**overrides_raw)
        if isinstance(overrides_raw, dict)
        else None
    )
    return EmploymentTypeRuleConfig(
        require_default_pair=bool(rule_row.require_default_pair),
        allowed_slot_types=rule_row.allowed_slot_types if isinstance(rule_row.allowed_slot_types, list) else None,
        annual_limit_overrides=annual_limit_overrides,
    )


def _build_response(
    session: Session, employment_type: EmploymentType
) -> EmploymentTypeResponse:
    """EmploymentType ORM オブジェクトからレスポンスモデルを構築する（ルールを含む）."""
    resp = EmploymentTypeResponse.model_validate(employment_type)
    resp.rule = _load_rule(session, employment_type.id)  # type: ignore[arg-type]
    return resp


def list_employment_types(
    session: Session, tenant_id: str
) -> list[EmploymentTypeResponse]:
    """テナントに属するEmploymentType一覧を取得する（名前昇順）.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        EmploymentType一覧のレスポンスモデルリスト。
    """
    employment_types = session.exec(
        select(EmploymentType)
        .where(EmploymentType.tenant_id == tenant_id)
        .order_by(EmploymentType.name)  # type: ignore[arg-type]
    ).all()
    return [_build_response(session, et) for et in employment_types]


def get_employment_type(
    session: Session, tenant_id: str, employment_type_id: uuid.UUID
) -> EmploymentTypeResponse:
    """指定したEmploymentTypeを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 取得対象のEmploymentTypeID。

    Returns:
        EmploymentTypeレスポンスモデル。

    Raises:
        HTTPException: EmploymentTypeが存在しない、または異なるテナントに属する場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )
    return _build_response(session, employment_type)


def update_employment_type(
    session: Session,
    tenant_id: str,
    employment_type_id: uuid.UUID,
    data: EmploymentTypeUpdate,
) -> EmploymentTypeResponse:
    """指定したEmploymentTypeを更新する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 更新対象のEmploymentTypeID。
        data: EmploymentType更新リクエストデータ。

    Returns:
        更新後のEmploymentTypeレスポンスモデル。

    Raises:
        HTTPException: EmploymentTypeが存在しない場合、または更新後の名前が重複する場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )

    if data.name is not None and data.name != employment_type.name:
        existing = session.exec(
            select(EmploymentType).where(
                EmploymentType.tenant_id == tenant_id,
                EmploymentType.name == data.name,
                EmploymentType.id != employment_type_id,  # type: ignore[arg-type]
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"EmploymentType '{data.name}' already exists.",
            )

    # is_default=True に更新する場合、他のレコードのデフォルトフラグを解除する（アトミック処理）
    if data.is_default is True:
        _clear_default_flag(session, tenant_id, exclude_id=employment_type_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employment_type, field, value)

    session.add(employment_type)
    session.commit()
    session.refresh(employment_type)
    return _build_response(session, employment_type)


def delete_employment_type(
    session: Session, tenant_id: str, employment_type_id: uuid.UUID
) -> None:
    """指定したEmploymentTypeを物理削除する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 削除対象のEmploymentTypeID。

    Raises:
        HTTPException: EmploymentTypeが存在しない場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )
    session.delete(employment_type)
    session.commit()


def get_employment_type_rule(
    session: Session, tenant_id: str, employment_type_id: uuid.UUID
) -> EmploymentTypeRuleConfig:
    """指定した雇用形態のルール設定を取得する.

    ルールが未設定の場合はデフォルト値（制限なし）を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 対象の雇用形態ID。

    Returns:
        EmploymentTypeRuleConfig（未設定の場合はデフォルト値）。

    Raises:
        HTTPException: 雇用形態が存在しない、または異なるテナントに属する場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )
    return _load_rule(session, employment_type_id) or EmploymentTypeRuleConfig()


def upsert_employment_type_rule(
    session: Session,
    tenant_id: str,
    employment_type_id: uuid.UUID,
    data: EmploymentTypeRuleUpdate,
) -> EmploymentTypeRuleConfig:
    """指定した雇用形態のルール設定をupsertする.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        employment_type_id: 対象の雇用形態ID。
        data: 更新データ。

    Returns:
        更新後の EmploymentTypeRuleConfig。

    Raises:
        HTTPException: 雇用形態が存在しない、または異なるテナントに属する場合。
    """
    employment_type = session.exec(
        select(EmploymentType).where(
            EmploymentType.id == employment_type_id,  # type: ignore[arg-type]
            EmploymentType.tenant_id == tenant_id,
        )
    ).first()
    if employment_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EmploymentType '{employment_type_id}' not found.",
        )

    rule_row = session.exec(
        select(EmploymentTypeRule).where(
            EmploymentTypeRule.employment_type_id == employment_type_id,  # type: ignore[arg-type]
        )
    ).first()

    if rule_row is None:
        rule_row = EmploymentTypeRule(
            employment_type_id=employment_type_id,
            tenant_id=tenant_id,
            require_default_pair=data.require_default_pair,
            allowed_slot_types=data.allowed_slot_types,
            annual_limit_overrides=data.annual_limit_overrides,
        )
    else:
        rule_row.require_default_pair = data.require_default_pair  # type: ignore[assignment]
        rule_row.allowed_slot_types = data.allowed_slot_types  # type: ignore[assignment]
        rule_row.annual_limit_overrides = data.annual_limit_overrides  # type: ignore[assignment]

    session.add(rule_row)
    session.commit()
    session.refresh(rule_row)

    return _load_rule(session, employment_type_id) or EmploymentTypeRuleConfig()
