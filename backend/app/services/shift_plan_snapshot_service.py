# backend/app/services/shift_plan_snapshot_service.py
"""シフトプランスナップショット（下書き保存）サービス層.

スナップショットの作成・一覧取得・復元を提供する。
保存時は同プランの件数が5を超えた場合、最古のものを自動削除する。
"""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import ShiftPlan, ShiftPlanSnapshot

# 保持するスナップショット件数の上限
_MAX_SNAPSHOTS = 5


def create_snapshot(
    session: Session,
    tenant_id: str,
    plan_id: uuid.UUID,
    snapshot_data: dict,
    created_by: str,
) -> ShiftPlanSnapshot:
    """スナップショットを作成する.

    保存後、同プランの件数が上限（5件）を超えた場合は最古のものを削除する。

    Args:
        session: DBセッション。
        tenant_id: テナントID。
        plan_id: シフトプランID。
        snapshot_data: CalendarState相当のJSONデータ。
        created_by: 保存者のClerk User ID。

    Returns:
        作成した ShiftPlanSnapshot。

    Raises:
        HTTPException 404: 指定された plan_id が存在しない、またはテナントに属さない場合。
    """
    # プランの存在・テナント検証
    plan = session.exec(
        select(ShiftPlan).where(
            ShiftPlan.id == plan_id,
            ShiftPlan.tenant_id == tenant_id,
        )
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="シフトプランが見つかりません。",
        )

    snapshot = ShiftPlanSnapshot(
        tenant_id=tenant_id,
        shift_plan_id=plan_id,
        snapshot_data=snapshot_data,
        created_by=created_by,
        created_at=datetime.utcnow(),
    )
    session.add(snapshot)
    session.flush()  # ID を確定させる

    # 上限超過分を削除（最古から削除）
    existing = session.exec(
        select(ShiftPlanSnapshot)
        .where(
            ShiftPlanSnapshot.shift_plan_id == plan_id,
            ShiftPlanSnapshot.tenant_id == tenant_id,
        )
        .order_by(ShiftPlanSnapshot.created_at.asc())  # type: ignore[union-attr]
    ).all()

    if len(existing) > _MAX_SNAPSHOTS:
        for old in existing[: len(existing) - _MAX_SNAPSHOTS]:
            session.delete(old)

    # ShiftPlan.updated_at を更新する
    plan.updated_at = datetime.utcnow()  # type: ignore[assignment]
    session.add(plan)

    session.commit()
    session.refresh(snapshot)
    return snapshot


def list_snapshots(
    session: Session,
    tenant_id: str,
    plan_id: uuid.UUID,
) -> list[ShiftPlanSnapshot]:
    """スナップショット一覧を取得する（降順、最大5件）.

    Args:
        session: DBセッション。
        tenant_id: テナントID。
        plan_id: シフトプランID。

    Returns:
        ShiftPlanSnapshot のリスト（新しい順）。
    """
    return list(
        session.exec(
            select(ShiftPlanSnapshot)
            .where(
                ShiftPlanSnapshot.shift_plan_id == plan_id,
                ShiftPlanSnapshot.tenant_id == tenant_id,
            )
            .order_by(ShiftPlanSnapshot.created_at.desc())  # type: ignore[union-attr]
            .limit(_MAX_SNAPSHOTS)
        ).all()
    )


def get_snapshot(
    session: Session,
    tenant_id: str,
    plan_id: uuid.UUID,
    snapshot_id: uuid.UUID,
) -> ShiftPlanSnapshot:
    """指定スナップショットを取得する.

    Args:
        session: DBセッション。
        tenant_id: テナントID。
        plan_id: シフトプランID。
        snapshot_id: スナップショットID。

    Returns:
        ShiftPlanSnapshot。

    Raises:
        HTTPException 404: スナップショットが存在しない場合。
    """
    snapshot = session.exec(
        select(ShiftPlanSnapshot).where(
            ShiftPlanSnapshot.id == snapshot_id,
            ShiftPlanSnapshot.shift_plan_id == plan_id,
            ShiftPlanSnapshot.tenant_id == tenant_id,
        )
    ).first()
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スナップショットが見つかりません。",
        )
    return snapshot
