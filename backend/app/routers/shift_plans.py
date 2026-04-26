# backend/app/routers/shift_plans.py
"""シフトプラン関連ルーター.

ベースパス: ``/api/shift-plans``
過去シフトデータの一括インポートエンドポイントを提供する。
"""

import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.models import PlanStatusEnum, ShiftPlan
from app.models.schemas import (
    ShiftPlanCreate,
    ShiftPlanDetailResponse,
    ShiftPlanImportResponse,
    ShiftPlanSnapshotCreate,
    ShiftPlanSnapshotResponse,
    ShiftPlanUpdatedAtResponse,
)
from app.services import shift_plan_import_service, shift_plan_snapshot_service

router = APIRouter(prefix="/api/shift-plans", tags=["shift-plans"])


@router.post(
    "/import",
    response_model=ShiftPlanImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_shift_plan(
    file: UploadFile,
    plan_status: PlanStatusEnum = Form(
        PlanStatusEnum.published,
        description="作成するシフトプランのステータス（draft / pending_approval / published）",
    ),
    created_by: str = Form(
        "import",
        description="作成者識別子（省略時は 'import'）",
    ),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftPlanImportResponse:
    """CSV/JSONファイルから過去シフトデータを一括インポートする.

    アップロードされたファイルをパースして、新規の ``ShiftPlan`` と紐づく
    ``ShiftSlot`` / ``ShiftAssignment`` を単一トランザクション内で作成する。
    過去データのため、全アサインに ``is_manual_override = True`` を設定し、
    シフトルール検証はスキップする。
    対象年月はファイル内の ``date`` カラムから自動検出する（全行が同一年月である必要あり）。

    CSVフォーマット例::

        date,slot_type,worker_id_1,worker_id_2
        2026-01-01,weekday_night,1234567,1357926

    JSONフォーマット例::

        [
          {
            "date": "2026-01-01",
            "slot_type": "weekday_night",
            "worker_ids": ["1234567", "1357926"]
          }
        ]

    ワーカーは職員番号（``employee_code``）で特定する。
    存在しない職員番号はスキップされ、レスポンスの ``skipped_worker_ids`` に含まれる。

    Args:
        file: アップロードするCSVまたはJSONファイル。
        plan_status: 作成するシフトプランのステータス。
        created_by: 作成者識別子。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        インポート結果（プランID・作成件数・スキップされたワーカーリスト）。

    Raises:
        HTTPException 415: 対応外のファイル形式の場合。
        HTTPException 422: パースエラー・フォーマット不正・複数年月混在の場合。
    """
    filename = file.filename or ""
    content_type_hint = _detect_content_type(filename, file.content_type or "")

    if content_type_hint not in ("csv", "json"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="対応しているファイル形式はCSV（.csv）またはJSON（.json）のみです。",
        )

    file_content = await file.read()

    return shift_plan_import_service.import_shift_plan(
        session=session,
        tenant_id=tenant_id,
        file_content=file_content,
        content_type=content_type_hint,
        plan_status=plan_status,
        created_by=created_by,
    )


@router.get("/", response_model=ShiftPlanDetailResponse | None)
def get_shift_plan(
    year_month: str = Query(
        ...,
        description="対象年月（YYYY-MM形式）。例: '2025-06'",
        pattern=r"^\d{4}-\d{2}$",
    ),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftPlanDetailResponse | None:
    """対象年月のシフトプランをスロット・アサイン情報込みで返す.

    該当するプランが存在しない場合は null を返す。

    Args:
        year_month: 対象年月（YYYY-MM形式）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        ShiftPlanDetailResponse、該当なければ null。
    """
    return shift_plan_import_service.get_shift_plan_by_year_month(
        session, tenant_id, year_month
    )


@router.post(
    "/", response_model=ShiftPlanDetailResponse, status_code=status.HTTP_201_CREATED
)
def create_shift_plan(
    payload: ShiftPlanCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftPlanDetailResponse:
    """空のシフトプランを新規作成する.

    スロットを持たない空のプランを作成する。
    同一年月のプランがすでに存在する場合は 409 を返す。

    Args:
        payload: 作成情報（target_year_month, title, created_by）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成した ShiftPlanDetailResponse。

    Raises:
        HTTPException 409: 同一年月のプランがすでに存在する場合。
    """
    return shift_plan_import_service.create_empty_shift_plan(
        session=session,
        tenant_id=tenant_id,
        target_year_month=payload.target_year_month,
        title=payload.title,
        created_by=payload.created_by,
    )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift_plan(
    plan_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> None:
    """指定したシフトプランを物理削除する.

    紐づく ``ShiftSlot`` / ``ShiftAssignment`` もカスケード削除される。
    リクエストユーザーのテナントに属するプランのみ削除可能。

    Args:
        plan_id: 削除対象のShiftPlan ID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Raises:
        HTTPException 404: 指定された ``plan_id`` が存在しない、または
            リクエストユーザーのテナントに属さない場合。
    """
    shift_plan_import_service.delete_shift_plan(session, tenant_id, plan_id)


def _detect_content_type(filename: str, mime: str) -> str:
    """ファイル名またはMIMEタイプからコンテンツ種別を判定する.

    ファイル拡張子を優先して判定し、次にMIMEタイプを参照する。

    Args:
        filename: アップロードファイル名。
        mime: HTTPコンテンツタイプ。

    Returns:
        "csv"、"json"、または未判定の場合は空文字列。
    """
    if filename.endswith(".csv"):
        return "csv"
    if filename.endswith(".json"):
        return "json"
    if mime in ("text/csv", "application/csv"):
        return "csv"
    if mime in ("application/json",):
        return "json"
    return ""


@router.post(
    "/{plan_id}/snapshots",
    response_model=ShiftPlanSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_snapshot(
    plan_id: uuid.UUID,
    payload: ShiftPlanSnapshotCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftPlanSnapshotResponse:
    """シフトプランの下書きスナップショットを作成する.

    スナップショットは最大5件保持され、6件目の保存時に最古のものが自動削除される。

    Args:
        plan_id: シフトプランID。
        payload: スナップショットデータ（snapshot_data, created_by）。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        作成した ShiftPlanSnapshotResponse。

    Raises:
        HTTPException 404: 指定された plan_id が存在しない場合。
    """
    snapshot = shift_plan_snapshot_service.create_snapshot(
        session=session,
        tenant_id=tenant_id,
        plan_id=plan_id,
        snapshot_data=payload.snapshot_data,
        created_by=payload.created_by,
    )
    return ShiftPlanSnapshotResponse.model_validate(snapshot)


@router.get(
    "/{plan_id}/snapshots",
    response_model=list[ShiftPlanSnapshotResponse],
)
def list_snapshots(
    plan_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> list[ShiftPlanSnapshotResponse]:
    """シフトプランのスナップショット一覧を取得する（新しい順、最大5件）.

    Args:
        plan_id: シフトプランID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        ShiftPlanSnapshotResponse のリスト。
    """
    snapshots = shift_plan_snapshot_service.list_snapshots(
        session=session,
        tenant_id=tenant_id,
        plan_id=plan_id,
    )
    return [ShiftPlanSnapshotResponse.model_validate(s) for s in snapshots]


@router.get(
    "/{plan_id}/updated-at",
    response_model=ShiftPlanUpdatedAtResponse,
)
def get_plan_updated_at(
    plan_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),
) -> ShiftPlanUpdatedAtResponse:
    """シフトプランの updated_at を返す（ローカルタイムスタンプとの比較用）.

    Args:
        plan_id: シフトプランID。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        ShiftPlanUpdatedAtResponse（updated_at フィールドを含む）。

    Raises:
        HTTPException 404: 指定された plan_id が存在しない場合。
    """
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
    return ShiftPlanUpdatedAtResponse(updated_at=plan.updated_at)  # type: ignore[arg-type]
