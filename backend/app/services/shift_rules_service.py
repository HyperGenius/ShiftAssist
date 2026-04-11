# backend/app/services/shift_rules_service.py
"""シフトルール定義サービス層.

シフト作成に関するビジネスルールを一元管理する。
フロントエンドとバックエンドが同一のルール定義を参照することで、
検証ロジックのSingle Source of Truthを実現する。
"""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.models import TenantRulesConfig
from app.models.rule_schemas import (
    AnnualShiftLimitsConfig,
    ShiftRulesConfig,
    ShiftRulesResponse,
    ShiftWarningsConfig,
)

# デフォルトのシフトルール定義（DBにレコードが存在しない場合に使用）
_DEFAULT_SHIFT_RULES = ShiftRulesResponse(
    shift_rules=ShiftRulesConfig(
        min_interval_days=10,
        require_skill_ranks=["rank_a"],
        allow_same_department=False,
        special_employment_shifts=["weekday_night"],
        workers_per_slot=2,
    ),
    warnings=ShiftWarningsConfig(
        avoid_consecutive_holidays=True,
        annual_shift_limits=AnnualShiftLimitsConfig(),
    ),
)


def get_shift_rules(session: Session, tenant_id: str) -> ShiftRulesResponse:
    """テナントのシフトルール定義を返す.

    DBにテナント固有のルールが保存されている場合はそれを返し、
    存在しない場合はデフォルト値を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。

    Returns:
        シフトルール定義レスポンス。
    """
    config = session.exec(
        select(TenantRulesConfig).where(
            TenantRulesConfig.tenant_id == tenant_id  # type: ignore[arg-type]
        )
    ).first()

    if config is None:
        return _DEFAULT_SHIFT_RULES

    return ShiftRulesResponse(
        shift_rules=ShiftRulesConfig(**config.rules_json),
        warnings=ShiftWarningsConfig(**config.warnings_json),
    )


def update_shift_rules(
    session: Session,
    tenant_id: str,
    payload: ShiftRulesResponse,
) -> ShiftRulesResponse:
    """テナントのシフトルール定義を更新（upsert）する.

    テナントのルール設定をDBに保存する。レコードが存在しない場合は新規作成し、
    存在する場合は上書き更新する。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        payload: 更新するルール定義。

    Returns:
        更新後のシフトルール定義レスポンス。
    """
    config = session.exec(
        select(TenantRulesConfig).where(
            TenantRulesConfig.tenant_id == tenant_id  # type: ignore[arg-type]
        )
    ).first()

    if config is None:
        config = TenantRulesConfig(
            tenant_id=tenant_id,
            rules_json=payload.shift_rules.model_dump(),
            warnings_json=payload.warnings.model_dump(),
        )
        session.add(config)
    else:
        config.rules_json = payload.shift_rules.model_dump()  # type: ignore[assignment]
        config.warnings_json = payload.warnings.model_dump()  # type: ignore[assignment]
        config.updated_at = datetime.now(UTC)  # type: ignore[assignment]

    session.commit()
    session.refresh(config)

    return ShiftRulesResponse(
        shift_rules=ShiftRulesConfig(**config.rules_json),
        warnings=ShiftWarningsConfig(**config.warnings_json),
    )
