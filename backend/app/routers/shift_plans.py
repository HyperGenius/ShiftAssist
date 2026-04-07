# backend/app/routers/shift_plans.py
"""シフトプラン関連ルーター.

ベースパス: ``/api/shift-plans``
過去シフトデータの一括インポートエンドポイントを提供する。
"""

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_tenant_id
from app.models.models import PlanStatusEnum
from app.models.schemas import ShiftPlanImportResponse
from app.services import shift_plan_import_service

router = APIRouter(prefix="/api/shift-plans", tags=["shift-plans"])


@router.post(
    "/import",
    response_model=ShiftPlanImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_shift_plan(
    file: UploadFile,
    target_year_month: str = Form(
        ...,
        description="対象年月（YYYY-MM形式）。例: '2025-12'",
        pattern=r"^\d{4}-\d{2}$",
    ),
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

    ワーカーは社員番号（``employee_no``）で特定する。
    存在しない社員番号はスキップされ、レスポンスの ``skipped_worker_ids`` に含まれる。

    Args:
        file: アップロードするCSVまたはJSONファイル。
        target_year_month: 対象年月（YYYY-MM形式）。
        plan_status: 作成するシフトプランのステータス。
        created_by: 作成者識別子。
        tenant_id: ``X-Tenant-Id`` ヘッダーから取得したテナントID。
        session: DBセッション。

    Returns:
        インポート結果（プランID・作成件数・スキップされたワーカーリスト）。

    Raises:
        HTTPException 415: 対応外のファイル形式の場合。
        HTTPException 422: パースエラーまたはフォーマット不正の場合。
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
        target_year_month=target_year_month,
        plan_status=plan_status,
        created_by=created_by,
    )


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
