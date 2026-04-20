# backend/app/services/custom_rule_service.py
"""カスタムルール CRUD サービス層.

すべての操作において ``tenant_id`` によるデータ分離を保証する。
"""

import uuid

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import CustomRule
from app.models.schemas import CustomRuleCreate, CustomRuleResponse, CustomRuleUpdate


def list_custom_rules(session: Session, tenant_id: str) -> list[CustomRuleResponse]:
    """テナントに属するカスタムルール一覧を取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。

    Returns:
        カスタムルール一覧のレスポンスモデルリスト（名前昇順）。
    """
    rules = session.exec(
        select(CustomRule)
        .where(CustomRule.tenant_id == tenant_id)
        .order_by(CustomRule.name)  # type: ignore[arg-type]
    ).all()
    return [CustomRuleResponse.model_validate(r) for r in rules]


def get_custom_rule(
    session: Session, tenant_id: str, rule_id: uuid.UUID
) -> CustomRuleResponse:
    """指定したカスタムルールを取得する.

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        rule_id: 取得対象のカスタムルール ID。

    Returns:
        カスタムルールレスポンスモデル。

    Raises:
        HTTPException: カスタムルールが存在しない場合。
    """
    rule = session.exec(
        select(CustomRule).where(
            CustomRule.id == rule_id,  # type: ignore[arg-type]
            CustomRule.tenant_id == tenant_id,
        )
    ).first()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CustomRule '{rule_id}' not found.",
        )
    return CustomRuleResponse.model_validate(rule)


def create_custom_rule(
    session: Session, tenant_id: str, data: CustomRuleCreate
) -> CustomRuleResponse:
    """新しいカスタムルールを作成する.

    Args:
        session: SQLModelセッション。
        tenant_id: 作成対象のテナントID。
        data: カスタムルール作成リクエストデータ。

    Returns:
        作成されたカスタムルールのレスポンスモデル。

    Raises:
        HTTPException: 同一テナント内でルール名が重複する場合（HTTP 409）。
    """
    existing = session.exec(
        select(CustomRule).where(
            CustomRule.tenant_id == tenant_id,
            CustomRule.name == data.name,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"CustomRule with name '{data.name}' already exists in this tenant.",
        )

    rule = CustomRule(
        tenant_id=tenant_id,
        name=data.name,
        allowed_slot_types=data.allowed_slot_types,
        annual_limit_overrides=data.annual_limit_overrides,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return CustomRuleResponse.model_validate(rule)


def update_custom_rule(
    session: Session,
    tenant_id: str,
    rule_id: uuid.UUID,
    data: CustomRuleUpdate,
) -> CustomRuleResponse:
    """指定したカスタムルールを更新する.

    ``model_dump(exclude_unset=True)`` により、指定されたフィールドのみを更新する。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        rule_id: 更新対象のカスタムルール ID。
        data: カスタムルール更新リクエストデータ。

    Returns:
        更新後のカスタムルールレスポンスモデル。

    Raises:
        HTTPException: カスタムルールが存在しない場合（HTTP 404）。
        HTTPException: 変更後の名前が既存ルールと重複する場合（HTTP 409）。
    """
    rule = session.exec(
        select(CustomRule).where(
            CustomRule.id == rule_id,  # type: ignore[arg-type]
            CustomRule.tenant_id == tenant_id,
        )
    ).first()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CustomRule '{rule_id}' not found.",
        )

    update_data = data.model_dump(exclude_unset=True)

    # 名前変更時の重複チェック
    if "name" in update_data and update_data["name"] != rule.name:
        duplicate = session.exec(
            select(CustomRule).where(
                CustomRule.tenant_id == tenant_id,
                CustomRule.name == update_data["name"],
            )
        ).first()
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"CustomRule with name '{update_data['name']}' already exists in this tenant.",
            )

    for field, value in update_data.items():
        setattr(rule, field, value)

    session.add(rule)
    session.commit()
    session.refresh(rule)
    return CustomRuleResponse.model_validate(rule)


def delete_custom_rule(
    session: Session, tenant_id: str, rule_id: uuid.UUID
) -> None:
    """指定したカスタムルールを物理削除する.

    削除されると、このルールをアサインされているWorkerの ``custom_rule_id`` は
    DB制約（ON DELETE SET NULL）により自動的に NULL にリセットされる。

    Args:
        session: SQLModelセッション。
        tenant_id: 対象テナントID。
        rule_id: 削除対象のカスタムルール ID。

    Raises:
        HTTPException: カスタムルールが存在しない場合。
    """
    rule = session.exec(
        select(CustomRule).where(
            CustomRule.id == rule_id,  # type: ignore[arg-type]
            CustomRule.tenant_id == tenant_id,
        )
    ).first()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CustomRule '{rule_id}' not found.",
        )
    session.delete(rule)
    session.commit()
