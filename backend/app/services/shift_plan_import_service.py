# backend/app/services/shift_plan_import_service.py
"""過去シフトデータ一括インポートサービス層.

CSV/JSONファイルをパースして ShiftPlan / ShiftSlot / ShiftAssignment を
単一トランザクション内でバルクインサートする。
過去データのため、全アサインに ``is_manual_override = True`` を設定し、
シフトルール検証は行わない。
"""

import csv
import io
import json
import uuid
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import (
    PlanStatusEnum,
    ShiftAssignment,
    ShiftPlan,
    ShiftSlot,
    SlotTypeEnum,
    Worker,
)
from app.models.schemas import ShiftPlanImportResponse

# CSV列名定数
_COL_DATE = "date"
_COL_SLOT_TYPE = "slot_type"
_WORKER_COL_PREFIX = "worker_id"

# 必須列
_REQUIRED_CSV_COLS = {_COL_DATE, _COL_SLOT_TYPE}


def _parse_date_str(value: str, row_index: int) -> date:
    """日付文字列をパースする.

    YYYY-MM-DD 形式のみサポート。

    Args:
        value: 日付文字列。
        row_index: エラーメッセージ用の行番号（0始まり）。

    Returns:
        dateオブジェクト。

    Raises:
        HTTPException: 不正なフォーマットの場合。
    """
    value = value.strip()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"行 {row_index + 1}: 日付フォーマットが不正です（YYYY-MM-DD 形式が必要）: '{value}'",
        ) from None


def _parse_slot_type(value: str, row_index: int) -> SlotTypeEnum:
    """SlotTypeEnum文字列をパースする.

    Args:
        value: 枠種別文字列。
        row_index: エラーメッセージ用の行番号（0始まり）。

    Returns:
        SlotTypeEnum値。

    Raises:
        HTTPException: 不正な枠種別の場合。
    """
    value = value.strip()
    try:
        return SlotTypeEnum(value)
    except ValueError:
        valid = ", ".join(e.value for e in SlotTypeEnum)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"行 {row_index + 1}: 不正な枠種別 '{value}'。有効な値: {valid}",
        ) from None


def _parse_csv_bytes(content: bytes) -> list[dict[str, str]]:
    """CSVバイト列をパースして行辞書のリストを返す.

    UTF-8（BOM付き含む）および Shift-JIS を試みる。

    Args:
        content: CSVファイルのバイト列。

    Returns:
        列名をキーとした行辞書のリスト。

    Raises:
        HTTPException: CSVフォーマット不正またはデコードエラーの場合。
    """
    for encoding in ("utf-8-sig", "utf-8", "shift_jis"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSVファイルのエンコーディングを判別できませんでした（UTF-8 または Shift-JIS が必要）。",
        )

    reader = csv.DictReader(io.StringIO(text))
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSVのパースに失敗しました: {exc}",
        ) from exc

    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSVにヘッダー行がありません。",
        )

    missing = _REQUIRED_CSV_COLS - set(reader.fieldnames)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSVに必須列が不足しています: {', '.join(sorted(missing))}",
        )

    return rows


def _parse_json_bytes(content: bytes) -> list[dict[str, object]]:
    """JSONバイト列をパースして行辞書のリストを返す.

    期待するフォーマット:
    ``[{"date": "YYYY-MM-DD", "slot_type": "...", "worker_ids": ["emp_no", ...]}, ...]``

    Args:
        content: JSONファイルのバイト列。

    Returns:
        行辞書のリスト。

    Raises:
        HTTPException: JSONフォーマット不正の場合。
    """
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"JSONのパースに失敗しました: {exc}",
        ) from exc

    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="JSONのルートはオブジェクトの配列（リスト）である必要があります。",
        )

    return data  # type: ignore[return-value]


def _extract_worker_ids_from_csv_row(row: dict[str, str]) -> list[str]:
    """CSV行からワーカー識別子を抽出する.

    ``worker_id``, ``worker_id_1``, ``worker_id_2``, ... など
    ``worker_id`` で始まる全列の値を収集する。

    Args:
        row: CSV行辞書。

    Returns:
        空文字列を除外したワーカー識別子リスト。
    """
    result: list[str] = []
    for key, val in row.items():
        if key.startswith(_WORKER_COL_PREFIX):
            stripped = val.strip()
            if stripped:
                result.append(stripped)
    return result


def _lookup_workers_by_employee_no(
    session: Session,
    tenant_id: str,
    employee_nos: list[str],
) -> tuple[dict[str, uuid.UUID], list[str]]:
    """社員番号からワーカーUUIDへのマッピングを構築する.

    存在しない社員番号はスキップ対象としてリストで返す。

    Args:
        session: DBセッション。
        tenant_id: テナントID。
        employee_nos: 社員番号のリスト（重複あり可）。

    Returns:
        (employee_no -> worker_id マップ, 存在しない社員番号リスト)
    """
    unique_nos = list(set(employee_nos))
    if not unique_nos:
        return {}, []

    workers = session.exec(
        select(Worker).where(
            Worker.employee_no.in_(unique_nos),  # type: ignore[attr-defined]
            Worker.tenant_id == tenant_id,
        )
    ).all()

    mapping: dict[str, uuid.UUID] = {}
    for w in workers:
        if w.employee_no is not None:
            mapping[w.employee_no] = w.id  # type: ignore[assignment]

    missing = [no for no in unique_nos if no not in mapping]
    return mapping, missing


def _detect_target_year_month(rows: list[dict[str, object]]) -> str:
    """パース済み行リストから対象年月を自動検出する.

    全行の date フィールドから YYYY-MM を収集し、単一の年月のみであることを検証する。

    Args:
        rows: 内部形式に正規化された行辞書のリスト。各 row["date"] は date オブジェクト。

    Returns:
        検出された対象年月（YYYY-MM形式）。

    Raises:
        HTTPException: 複数の年月が混在している場合。
    """
    year_months: set[str] = set()
    for row in rows:
        d = row["date"]
        if isinstance(d, date):
            year_months.add(d.strftime("%Y-%m"))

    if len(year_months) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"ファイル内に複数の年月が混在しています: {', '.join(sorted(year_months))}。"
                "1回のインポートは単一の年月のみ対象にしてください。"
            ),
        )

    return next(iter(year_months))


def import_shift_plan(
    session: Session,
    tenant_id: str,
    file_content: bytes,
    content_type: str,
    plan_status: PlanStatusEnum = PlanStatusEnum.published,
    created_by: str = "import",
) -> ShiftPlanImportResponse:
    """CSVまたはJSONファイルから過去シフトデータを一括インポートする.

    単一トランザクション内で ShiftPlan / ShiftSlot / ShiftAssignment を作成する。
    エラーが発生した場合はロールバックし、中途半端なデータが残らないようにする。
    全アサインに ``is_manual_override = True`` を設定し、ルール検証をスキップする。
    対象年月はファイル内の date カラムから自動検出する。全行が同一年月である必要がある。

    Args:
        session: DBセッション。
        tenant_id: テナントID。
        file_content: アップロードファイルのバイト列。
        content_type: ファイルのコンテンツタイプ（"csv" または "json"）。
        plan_status: 作成するシフトプランのステータス（デフォルト: published）。
        created_by: 作成者識別子（デフォルト: "import"）。

    Returns:
        インポート結果レスポンス。

    Raises:
        HTTPException: パースエラー・フォーマット不正・複数年月混在・DB制約エラーの場合。
    """
    # --- ファイルパース ---
    if content_type == "json":
        raw_rows = _parse_json_bytes(file_content)
        rows = _normalize_json_rows(raw_rows)
    else:
        raw_csv_rows = _parse_csv_bytes(file_content)
        rows = _normalize_csv_rows(raw_csv_rows)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ファイルにデータ行がありません。",
        )

    # --- ファイル内の日付から対象年月を自動検出 ---
    target_year_month = _detect_target_year_month(rows)

    # --- 全ワーカー社員番号を収集して一括ルックアップ ---
    all_employee_nos: list[str] = []
    for row in rows:
        all_employee_nos.extend(row["worker_nos"])

    worker_map, missing_nos = _lookup_workers_by_employee_no(
        session, tenant_id, all_employee_nos
    )

    # --- トランザクション内でバルクインサート ---
    try:
        # ShiftPlan 作成
        plan_title = f"{target_year_month} インポート"
        plan = ShiftPlan(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            title=plan_title,
            target_year_month=target_year_month,
            status=plan_status,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )
        session.add(plan)
        session.flush()  # plan.id を確定させる

        slots_created = 0
        assignments_created = 0
        skipped: list[str] = list(missing_nos)

        for row in rows:
            slot_date = row["date"]
            slot_type = row["slot_type"]
            worker_nos = row["worker_nos"]

            # ShiftSlot 作成
            slot = ShiftSlot(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                plan_id=plan.id,
                date=datetime.combine(slot_date, datetime.min.time()),
                slot_type=slot_type,
            )
            session.add(slot)
            session.flush()  # slot.id を確定させる
            slots_created += 1

            # ShiftAssignment 作成（is_manual_override=True で強制保存）
            seen_worker_ids: set[uuid.UUID] = set()
            for emp_no in worker_nos:
                worker_id = worker_map.get(emp_no)
                if worker_id is None:
                    # 既にスキップリストに追加済み（_lookup_workers_by_employee_no で収集）
                    continue
                if worker_id in seen_worker_ids:
                    # 同一スロット内での重複をスキップ
                    continue
                seen_worker_ids.add(worker_id)

                assignment = ShiftAssignment(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    slot_id=slot.id,
                    worker_id=worker_id,
                    is_manual_override=True,
                    created_at=datetime.utcnow(),
                )
                session.add(assignment)
                assignments_created += 1

        session.commit()

    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"インポート処理中にエラーが発生しました: {exc}",
        ) from exc

    return ShiftPlanImportResponse(
        plan_id=plan.id,
        target_year_month=target_year_month,
        status=plan_status,
        slots_created=slots_created,
        assignments_created=assignments_created,
        skipped_worker_ids=sorted(set(skipped)),
    )


def _normalize_csv_rows(
    raw_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    """CSV行辞書リストを内部形式に正規化する.

    Args:
        raw_rows: csv.DictReader から得た行辞書リスト。

    Returns:
        {"date": date, "slot_type": SlotTypeEnum, "worker_nos": list[str]} のリスト。
    """
    result: list[dict[str, object]] = []
    for i, row in enumerate(raw_rows):
        shift_date = _parse_date_str(row[_COL_DATE], i)
        slot_type = _parse_slot_type(row[_COL_SLOT_TYPE], i)
        worker_nos = _extract_worker_ids_from_csv_row(row)
        result.append({"date": shift_date, "slot_type": slot_type, "worker_nos": worker_nos})
    return result


def _normalize_json_rows(
    raw_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """JSON行辞書リストを内部形式に正規化する.

    期待するフォーマット（1要素）:
    ``{"date": "YYYY-MM-DD", "slot_type": "...", "worker_ids": ["emp_no", ...]}``

    Args:
        raw_rows: JSONからパースされた行辞書リスト。

    Returns:
        {"date": date, "slot_type": SlotTypeEnum, "worker_nos": list[str]} のリスト。
    """
    result: list[dict[str, object]] = []
    for i, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"JSON行 {i + 1}: オブジェクト形式である必要があります。",
            )
        if _COL_DATE not in row or _COL_SLOT_TYPE not in row:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"JSON行 {i + 1}: 'date' および 'slot_type' フィールドが必要です。",
            )

        shift_date = _parse_date_str(str(row[_COL_DATE]), i)
        slot_type = _parse_slot_type(str(row[_COL_SLOT_TYPE]), i)

        worker_ids_raw = row.get("worker_ids", [])
        if not isinstance(worker_ids_raw, list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"JSON行 {i + 1}: 'worker_ids' はリスト形式である必要があります。",
            )
        worker_nos = [str(w).strip() for w in worker_ids_raw if str(w).strip()]

        result.append({"date": shift_date, "slot_type": slot_type, "worker_nos": worker_nos})
    return result
