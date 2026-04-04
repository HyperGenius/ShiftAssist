# backend/app/services/worker_upload_service.py
"""Worker CSV/Excelアップロードサービス層.

CSV/ExcelファイルをパースしてWorkerを一括Upsertする。
名前解決（役職名・支所名・課名）、バリデーション、Dry-run（差分プレビュー）をサポートする。
"""

import csv
import io
import re
import uuid
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.models import (
    Branch,
    Department,
    Position,
    TenantSkillRank,
    TransferTypeEnum,
    Worker,
)
from app.models.schemas import (
    WorkerResponse,
    WorkerUploadDiffItem,
    WorkerUploadErrorRow,
    WorkerUploadPreviewResponse,
    WorkerUploadRowValues,
    WorkerUploadUpsertResponse,
)

# CSV/Excelの列名（日本語ヘッダー）マッピング
_COL_EMPLOYEE_CODE = "職員番号"
_COL_NAME = "氏名"
_COL_BIRTH_DATE = "生年月日"
_COL_SKILL_ACQUIRED_AT = "現在のスキル取得日"
_COL_POSITION_NAME = "役職名"
_COL_BRANCH_NAME = "支所名"
_COL_DEPARTMENT_NAME = "課名"
_COL_TRANSFER_TYPE = "異動種別"
_COL_TRANSFER_SCHEDULED_MONTH = "異動予定月"
_COL_IS_CROSS_DIVISION = "事業本部変更の有無"
_COL_SKILL_RANK_NAME = "スキルランク名"

# 必須列
_REQUIRED_COLS = {_COL_EMPLOYEE_CODE, _COL_NAME}

# 異動種別の日本語→Enum変換マップ
_TRANSFER_TYPE_MAP: dict[str, TransferTypeEnum] = {
    "異動なし": TransferTypeEnum.no_transfer,
    "転入": TransferTypeEnum.transfer_in,
    "転出": TransferTypeEnum.transfer_out,
    "no_transfer": TransferTypeEnum.no_transfer,
    "transfer_in": TransferTypeEnum.transfer_in,
    "transfer_out": TransferTypeEnum.transfer_out,
}

# 真偽値の日本語→bool変換マップ
_BOOL_TRUE_VALS = {"true", "1", "yes", "あり", "○", "◯"}
_BOOL_FALSE_VALS = {"false", "0", "no", "なし", "×", "✕"}

# 異動予定月フォーマット（YYYY-MM）
_TRANSFER_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _parse_date(value: str, field_name: str) -> date | None:
    """日付文字列をパースする.

    YYYY-MM-DD または YYYY/MM/DD 形式をサポート。

    Args:
        value: 日付文字列。空文字列の場合はNoneを返す。
        field_name: エラーメッセージ用フィールド名。

    Returns:
        dateオブジェクト、または空の場合None。

    Raises:
        ValueError: 日付フォーマットが不正な場合。
    """
    v = value.strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"'{field_name}' の日付フォーマットが不正です（'{v}'）。"
        "YYYY-MM-DD または YYYY/MM/DD 形式で入力してください。"
    )


def _parse_bool(value: str, field_name: str) -> bool | None:
    """真偽値文字列をパースする.

    Args:
        value: 真偽値文字列。空文字列の場合はNoneを返す。
        field_name: エラーメッセージ用フィールド名。

    Returns:
        boolオブジェクト、または空の場合None。

    Raises:
        ValueError: 真偽値フォーマットが不正な場合。
    """
    v = value.strip().lower()
    if not v:
        return None
    if v in _BOOL_TRUE_VALS:
        return True
    if v in _BOOL_FALSE_VALS:
        return False
    raise ValueError(
        f"'{field_name}' の値が不正です（'{value}'）。"
        "「あり/なし」「true/false」「1/0」のいずれかで入力してください。"
    )


def _parse_transfer_type(value: str) -> TransferTypeEnum | None:
    """異動種別文字列をパースする.

    Args:
        value: 異動種別文字列。空文字列の場合はNoneを返す。

    Returns:
        TransferTypeEnumオブジェクト、または空の場合None。

    Raises:
        ValueError: 異動種別が不正な場合。
    """
    v = value.strip()
    if not v:
        return None
    if v in _TRANSFER_TYPE_MAP:
        return _TRANSFER_TYPE_MAP[v]
    valid = "、".join(_TRANSFER_TYPE_MAP.keys())
    raise ValueError(f"'異動種別' の値が不正です（'{v}'）。有効な値: {valid}")


# --- マスタ一括取得ヘルパー ---


def _fetch_positions_by_name(
    session: Session, tenant_id: str
) -> dict[str, uuid.UUID]:
    """テナントの全役職を名前→IDマップで取得する."""
    rows = session.exec(
        select(Position).where(Position.tenant_id == tenant_id)
    ).all()
    return {str(row.name): row.id for row in rows}  # type: ignore[misc]


def _fetch_branches_by_name(
    session: Session, tenant_id: str
) -> dict[str, uuid.UUID]:
    """テナントの全支所を名前→IDマップで取得する."""
    rows = session.exec(
        select(Branch).where(Branch.tenant_id == tenant_id)
    ).all()
    return {str(row.name): row.id for row in rows}  # type: ignore[misc]


def _fetch_departments_by_name(
    session: Session, tenant_id: str
) -> dict[str, Department]:
    """テナントの全課（論理削除済み除く）を名前→オブジェクトマップで取得する."""
    rows = session.exec(
        select(Department).where(
            Department.tenant_id == tenant_id,
            Department.deleted_at.is_(None),  # type: ignore[attr-defined]
        )
    ).all()
    return {str(row.name): row for row in rows}


def _fetch_skill_ranks_by_name(
    session: Session, tenant_id: str
) -> dict[str, uuid.UUID]:
    """テナントの全スキルランクを名前→IDマップで取得する."""
    rows = session.exec(
        select(TenantSkillRank).where(TenantSkillRank.tenant_id == tenant_id)
    ).all()
    return {str(row.name): row.id for row in rows}  # type: ignore[misc]


def _fetch_workers_by_employee_code(
    session: Session, tenant_id: str, codes: list[str]
) -> dict[str, Worker]:
    """指定した職員番号一覧に対応するWorkerを取得してdict化する."""
    if not codes:
        return {}
    rows = session.exec(
        select(Worker).where(
            Worker.tenant_id == tenant_id,
            Worker.employee_code.in_(codes),  # type: ignore[attr-defined]
        )
    ).all()
    return {str(row.employee_code): row for row in rows}


# --- CSVパース ---


def parse_csv_bytes(content: bytes) -> list[dict[str, str]]:
    """CSVバイト列を行データのリストに変換する.

    Args:
        content: CSVファイルのバイト列。UTF-8またはSJISエンコーディングをサポート。

    Returns:
        各行をカラム名→値の辞書に変換したリスト。

    Raises:
        HTTPException: ヘッダー行が存在しない、または必須列が不足している場合。
    """
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "shift_jis", "cp932"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSVファイルのエンコーディングを認識できません。UTF-8またはShift-JIS形式で保存してください。",
        )

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSVにヘッダー行がありません。",
        )

    missing = _REQUIRED_COLS - set(reader.fieldnames)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"CSVに必須列が不足しています: {', '.join(sorted(missing))}",
        )

    return list(reader)


def _load_excel_rows(content: bytes) -> list[tuple]:
    """Excelバイト列からシート行を読み込む（openpyxl依存）."""
    import openpyxl  # noqa: PLC0415

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Excelファイルにシートがありません。",
        )
    return list(ws.iter_rows(values_only=True))


def parse_excel_bytes(content: bytes) -> list[dict[str, str]]:
    """Excelバイト列を行データのリストに変換する.

    Args:
        content: Excelファイル（.xlsx）のバイト列。

    Returns:
        各行をカラム名→値の辞書に変換したリスト。

    Raises:
        HTTPException: ヘッダー行が存在しない、または必須列が不足している場合。
        HTTPException: Excelファイルの読み込みに失敗した場合。
    """
    try:
        rows = _load_excel_rows(content)
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Excelファイルの処理ライブラリが利用できません。",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Excelファイルの読み込みに失敗しました: {e}",
        ) from e

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Excelファイルにデータがありません。",
        )

    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    missing = _REQUIRED_COLS - set(headers)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Excelに必須列が不足しています: {', '.join(sorted(missing))}",
        )

    return [
        {
            col: str(val).strip() if val is not None else ""
            for col, val in zip(headers, row, strict=False)
            if col
        }
        for row in rows[1:]
    ]


# --- 行データ処理 ---


class _ParsedRow:
    """パース済みの1行データ（内部使用）."""

    __slots__ = (
        "row_index",
        "employee_code",
        "name",
        "birth_date",
        "skill_acquired_at",
        "position_name",
        "branch_name",
        "department_name",
        "transfer_type",
        "transfer_scheduled_month",
        "is_cross_division_transfer",
        "skill_rank_name",
        "position_id",
        "department_id",
        "skill_rank_id",
        "errors",
    )

    def __init__(self, row_index: int) -> None:
        """初期化."""
        self.row_index = row_index
        self.employee_code: str = ""
        self.name: str = ""
        self.birth_date: date | None = None
        self.skill_acquired_at: date | None = None
        self.position_name: str | None = None
        self.branch_name: str | None = None
        self.department_name: str | None = None
        self.transfer_type: TransferTypeEnum | None = None
        self.transfer_scheduled_month: str | None = None
        self.is_cross_division_transfer: bool | None = None
        self.skill_rank_name: str | None = None
        self.position_id: uuid.UUID | None = None
        self.department_id: uuid.UUID | None = None
        self.skill_rank_id: uuid.UUID | None = None
        self.errors: list[str] = []


def _parse_scalar_fields(pr: _ParsedRow, row: dict[str, str]) -> None:
    """行から日付・真偽値・選択肢フィールドをパースして _ParsedRow に設定する."""
    i = pr.row_index

    try:
        pr.birth_date = _parse_date(row.get(_COL_BIRTH_DATE, ""), _COL_BIRTH_DATE)
    except ValueError as e:
        pr.errors.append(str(e))

    try:
        pr.skill_acquired_at = _parse_date(
            row.get(_COL_SKILL_ACQUIRED_AT, ""), _COL_SKILL_ACQUIRED_AT
        )
    except ValueError as e:
        pr.errors.append(str(e))

    try:
        pr.transfer_type = _parse_transfer_type(row.get(_COL_TRANSFER_TYPE, ""))
    except ValueError as e:
        pr.errors.append(str(e))

    tsm = row.get(_COL_TRANSFER_SCHEDULED_MONTH, "").strip()
    if tsm:
        if not _TRANSFER_MONTH_RE.match(tsm):
            pr.errors.append(
                f"行{i}: '異動予定月' のフォーマットが不正です（'{tsm}'）。YYYY-MM形式で入力してください。"
            )
        else:
            pr.transfer_scheduled_month = tsm

    try:
        pr.is_cross_division_transfer = _parse_bool(
            row.get(_COL_IS_CROSS_DIVISION, ""), _COL_IS_CROSS_DIVISION
        )
    except ValueError as e:
        pr.errors.append(str(e))


def _resolve_names_for_row(
    pr: _ParsedRow,
    row: dict[str, str],
    position_map: dict[str, uuid.UUID],
    branch_map: dict[str, uuid.UUID],
    department_map: dict[str, Department],
    skill_rank_map: dict[str, uuid.UUID],
) -> None:
    """行の名前フィールドをマスタと照合してIDに解決し _ParsedRow に設定する."""
    i = pr.row_index

    pos_name = row.get(_COL_POSITION_NAME, "").strip()
    if pos_name:
        pr.position_name = pos_name
        pos_id = position_map.get(pos_name)
        if pos_id is None:
            pr.errors.append(f"行{i}: 役職名『{pos_name}』は登録されていません。")
        else:
            pr.position_id = pos_id

    br_name = row.get(_COL_BRANCH_NAME, "").strip()
    if br_name:
        pr.branch_name = br_name
        if br_name not in branch_map:
            pr.errors.append(f"行{i}: 支所名『{br_name}』は登録されていません。")

    dept_name = row.get(_COL_DEPARTMENT_NAME, "").strip()
    if dept_name:
        pr.department_name = dept_name
        dept = department_map.get(dept_name)
        if dept is None:
            pr.errors.append(f"行{i}: 課名『{dept_name}』は登録されていません。")
        else:
            pr.department_id = dept.id  # type: ignore[assignment]

    sr_name = row.get(_COL_SKILL_RANK_NAME, "").strip()
    if sr_name:
        pr.skill_rank_name = sr_name
        sr_id = skill_rank_map.get(sr_name)
        if sr_id is None:
            pr.errors.append(f"行{i}: スキルランク名『{sr_name}』は登録されていません。")
        else:
            pr.skill_rank_id = sr_id


def _parse_single_row(
    row_index: int,
    row: dict[str, str],
    position_map: dict[str, uuid.UUID],
    branch_map: dict[str, uuid.UUID],
    department_map: dict[str, Department],
    skill_rank_map: dict[str, uuid.UUID],
) -> _ParsedRow:
    """1行をパース・バリデーション・名前解決して _ParsedRow を返す."""
    pr = _ParsedRow(row_index)

    ec = row.get(_COL_EMPLOYEE_CODE, "").strip()
    if not ec:
        pr.errors.append(f"行{row_index}: '{_COL_EMPLOYEE_CODE}' は必須です。")
    pr.employee_code = ec

    name = row.get(_COL_NAME, "").strip()
    if not name:
        pr.errors.append(f"行{row_index}: '{_COL_NAME}' は必須です。")
    pr.name = name

    _parse_scalar_fields(pr, row)
    _resolve_names_for_row(pr, row, position_map, branch_map, department_map, skill_rank_map)

    return pr


def _parse_rows(
    raw_rows: list[dict[str, str]],
    position_map: dict[str, uuid.UUID],
    branch_map: dict[str, uuid.UUID],
    department_map: dict[str, Department],
    skill_rank_map: dict[str, uuid.UUID],
) -> list[_ParsedRow]:
    """生の行データをパース・バリデーション・名前解決する.

    Args:
        raw_rows: CSVまたはExcelから読み込んだ生の行データリスト。
        position_map: 役職名→UUID マッピング。
        branch_map: 支所名→UUID マッピング。
        department_map: 課名→Departmentオブジェクト マッピング。
        skill_rank_map: スキルランク名→UUID マッピング。

    Returns:
        パース済み行データのリスト（エラーがあってもリストに含まれる）。
    """
    return [
        _parse_single_row(i, row, position_map, branch_map, department_map, skill_rank_map)
        for i, row in enumerate(raw_rows, start=2)
    ]


# --- Dry-run（プレビュー） ---


def _worker_to_row_values(
    worker: Worker, dept_name: str | None, pos_name: str | None
) -> WorkerUploadRowValues:
    """WorkerオブジェクトをWorkerUploadRowValuesに変換する."""
    return WorkerUploadRowValues(
        name=str(worker.name),
        department_name=dept_name,
        position_name=pos_name,
        birth_date=str(worker.birth_date) if worker.birth_date else None,
        skill_acquired_at=str(worker.skill_acquired_at) if worker.skill_acquired_at else None,
        transfer_type=str(worker.transfer_type.value) if worker.transfer_type else None,
        transfer_scheduled_month=(
            str(worker.transfer_scheduled_month) if worker.transfer_scheduled_month else None
        ),
        is_cross_division_transfer=(
            bool(worker.is_cross_division_transfer)
            if worker.is_cross_division_transfer is not None
            else None
        ),
    )


def _parsed_to_row_values(pr: _ParsedRow) -> WorkerUploadRowValues:
    """パース済み行をWorkerUploadRowValuesに変換する."""
    return WorkerUploadRowValues(
        name=pr.name,
        department_name=pr.department_name,
        position_name=pr.position_name,
        birth_date=str(pr.birth_date) if pr.birth_date else None,
        skill_acquired_at=str(pr.skill_acquired_at) if pr.skill_acquired_at else None,
        transfer_type=str(pr.transfer_type.value) if pr.transfer_type else None,
        transfer_scheduled_month=pr.transfer_scheduled_month,
        is_cross_division_transfer=pr.is_cross_division_transfer,
    )


def _is_row_changed(before: WorkerUploadRowValues, after: WorkerUploadRowValues) -> bool:
    """更新前後の値を比較して変更があるか判定する."""
    checks = [
        before.name != after.name,
        after.department_name is not None and before.department_name != after.department_name,
        after.position_name is not None and before.position_name != after.position_name,
        after.birth_date is not None and before.birth_date != after.birth_date,
        after.skill_acquired_at is not None and before.skill_acquired_at != after.skill_acquired_at,
        after.transfer_type is not None and before.transfer_type != after.transfer_type,
        after.transfer_scheduled_month is not None and before.transfer_scheduled_month != after.transfer_scheduled_month,
        after.is_cross_division_transfer is not None and before.is_cross_division_transfer != after.is_cross_division_transfer,
    ]
    return any(checks)


def _build_diff_for_existing(
    pr: _ParsedRow,
    existing: Worker,
    dept_id_to_name: dict[str, str],
    pos_id_to_name: dict[str, str],
) -> tuple[WorkerUploadDiffItem, bool]:
    """既存Workerと新データを比較して差分アイテムを構築する.

    Returns:
        (WorkerUploadDiffItem, is_updated) のタプル。
    """
    before_vals = _worker_to_row_values(
        existing,
        dept_id_to_name.get(str(existing.department_id)),
        pos_id_to_name.get(str(existing.position_id)) if existing.position_id else None,
    )
    after_vals = _parsed_to_row_values(pr)
    changed = _is_row_changed(before_vals, after_vals)
    action = "update" if changed else "no_change"
    return (
        WorkerUploadDiffItem(
            row_index=pr.row_index,
            employee_code=pr.employee_code,
            action=action,
            before=before_vals,
            after=after_vals,
        ),
        changed,
    )


def preview_upload(
    session: Session,
    tenant_id: str,
    raw_rows: list[dict[str, str]],
) -> WorkerUploadPreviewResponse:
    """CSV/Excelアップロードの差分プレビュー（Dry-run）を返す.

    実際のDB更新は行わない。バリデーションエラーがある行と、
    エラーがない行の差分（新規/更新/変更なし）を返す。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        raw_rows: CSVまたはExcelから読み込んだ生の行データリスト。

    Returns:
        プレビューレスポンス（エラー行、差分リスト、件数）。
    """
    position_map = _fetch_positions_by_name(session, tenant_id)
    branch_map = _fetch_branches_by_name(session, tenant_id)
    department_map = _fetch_departments_by_name(session, tenant_id)
    skill_rank_map = _fetch_skill_ranks_by_name(session, tenant_id)

    parsed_rows = _parse_rows(raw_rows, position_map, branch_map, department_map, skill_rank_map)

    valid_codes = [pr.employee_code for pr in parsed_rows if pr.employee_code and not pr.errors]
    existing_map = _fetch_workers_by_employee_code(session, tenant_id, valid_codes)

    dept_id_to_name = {str(dept.id): name for name, dept in department_map.items()}
    pos_id_to_name = {str(v): k for k, v in position_map.items()}

    error_rows: list[WorkerUploadErrorRow] = []
    diff_items: list[WorkerUploadDiffItem] = []
    create_count = update_count = no_change_count = 0

    for pr in parsed_rows:
        if pr.errors:
            error_rows.append(
                WorkerUploadErrorRow(
                    row_index=pr.row_index,
                    employee_code=pr.employee_code or None,
                    errors=pr.errors,
                )
            )
            continue

        existing = existing_map.get(pr.employee_code)
        if existing is None:
            diff_items.append(
                WorkerUploadDiffItem(
                    row_index=pr.row_index,
                    employee_code=pr.employee_code,
                    action="create",
                    before=None,
                    after=_parsed_to_row_values(pr),
                )
            )
            create_count += 1
        else:
            diff_item, changed = _build_diff_for_existing(
                pr, existing, dept_id_to_name, pos_id_to_name
            )
            diff_items.append(diff_item)
            if changed:
                update_count += 1
            else:
                no_change_count += 1

    return WorkerUploadPreviewResponse(
        diff_items=diff_items,
        error_rows=error_rows,
        create_count=create_count,
        update_count=update_count,
        no_change_count=no_change_count,
        error_count=len(error_rows),
        has_errors=len(error_rows) > 0,
    )


# --- Upsert実行 ---


def _validate_upload_rows(parsed_rows: list[_ParsedRow]) -> list[_ParsedRow]:
    """バリデーション済みの有効な行のみ返す。エラーがあれば例外を送出する.

    Raises:
        HTTPException: バリデーションエラーが1件以上ある場合（HTTP 422）。
        HTTPException: 有効なデータ行がない場合（HTTP 422）。
        HTTPException: 重複する職員番号がある場合（HTTP 422）。
    """
    error_rows = [pr for pr in parsed_rows if pr.errors]
    if error_rows:
        msgs = [msg for pr in error_rows for msg in pr.errors]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"バリデーションエラーがあるため実行できません: {'; '.join(msgs)}",
        )

    valid_rows = [pr for pr in parsed_rows if pr.employee_code]
    if not valid_rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="有効なデータ行がありません。",
        )

    _check_duplicate_codes([pr.employee_code for pr in valid_rows])
    return valid_rows


def _check_duplicate_codes(codes: list[str]) -> None:
    """職員番号の重複チェック。重複があれば422を送出する."""
    if len(codes) == len(set(codes)):
        return
    seen: set[str] = set()
    duplicates: list[str] = []
    for code in codes:
        if code in seen:
            duplicates.append(code)
        seen.add(code)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"重複する職員番号が含まれています: {', '.join(duplicates)}",
    )


def _apply_updates_to_worker(existing: Worker, pr: _ParsedRow) -> None:
    """既存WorkerにパースされたフィールドをNone以外の値で上書きする."""
    existing.name = pr.name  # type: ignore[assignment]
    if pr.department_id is not None:
        existing.department_id = pr.department_id  # type: ignore[assignment]
    if pr.position_id is not None:
        existing.position_id = pr.position_id  # type: ignore[assignment]
    if pr.skill_rank_id is not None:
        existing.skill_rank_id = pr.skill_rank_id  # type: ignore[assignment]
    if pr.birth_date is not None:
        existing.birth_date = pr.birth_date  # type: ignore[assignment]
    if pr.skill_acquired_at is not None:
        existing.skill_acquired_at = pr.skill_acquired_at  # type: ignore[assignment]
    if pr.transfer_type is not None:
        existing.transfer_type = pr.transfer_type  # type: ignore[assignment]
    if pr.transfer_scheduled_month is not None:
        existing.transfer_scheduled_month = pr.transfer_scheduled_month  # type: ignore[assignment]
    if pr.is_cross_division_transfer is not None:
        existing.is_cross_division_transfer = pr.is_cross_division_transfer  # type: ignore[assignment]


def _upsert_single_row(
    session: Session,
    tenant_id: str,
    pr: _ParsedRow,
    existing: Worker | None,
) -> tuple[Worker | None, bool]:
    """1行のUpsertを実行する.

    Returns:
        (Workerオブジェクト, is_created) のタプル。
        スキップした場合は (None, False) を返す。
    """
    if existing is None:
        if pr.department_id is None:
            return None, False
        worker = Worker(
            tenant_id=tenant_id,
            employee_code=pr.employee_code,
            name=pr.name,
            department_id=pr.department_id,
            skill_rank_id=pr.skill_rank_id,
            position_id=pr.position_id,
            birth_date=pr.birth_date,
            skill_acquired_at=pr.skill_acquired_at,
            transfer_type=pr.transfer_type,
            transfer_scheduled_month=pr.transfer_scheduled_month,
            is_cross_division_transfer=pr.is_cross_division_transfer,
        )
        session.add(worker)
        return worker, True

    _apply_updates_to_worker(existing, pr)
    session.add(existing)
    return existing, False


def execute_upload(
    session: Session,
    tenant_id: str,
    raw_rows: list[dict[str, str]],
) -> WorkerUploadUpsertResponse:
    """CSV/ExcelアップロードをUpsert実行する.

    バリデーションエラーがある行はスキップし、エラーのない行のみUpsertする。
    ``employee_code`` と ``tenant_id`` の複合キーでUpsertを行う。

    Args:
        session: SQLModelセッション。
        tenant_id: テナントID。
        raw_rows: CSVまたはExcelから読み込んだ生の行データリスト。

    Returns:
        Upsert実行結果（作成件数、更新件数、処理済みWorkerリスト）。

    Raises:
        HTTPException: バリデーションエラーが1件以上ある場合（HTTP 422）。
    """
    position_map = _fetch_positions_by_name(session, tenant_id)
    branch_map = _fetch_branches_by_name(session, tenant_id)
    department_map = _fetch_departments_by_name(session, tenant_id)
    skill_rank_map = _fetch_skill_ranks_by_name(session, tenant_id)

    parsed_rows = _parse_rows(raw_rows, position_map, branch_map, department_map, skill_rank_map)
    valid_rows = _validate_upload_rows(parsed_rows)

    codes = [pr.employee_code for pr in valid_rows]
    existing_map = _fetch_workers_by_employee_code(session, tenant_id, codes)

    created = updated = 0
    result_workers: list[Worker] = []

    for pr in valid_rows:
        worker, is_new = _upsert_single_row(
            session, tenant_id, pr, existing_map.get(pr.employee_code)
        )
        if worker is None:
            continue
        if is_new:
            created += 1
        else:
            updated += 1
        result_workers.append(worker)

    session.commit()
    for w in result_workers:
        session.refresh(w)

    return WorkerUploadUpsertResponse(
        created=created,
        updated=updated,
        items=[WorkerResponse.model_validate(w) for w in result_workers],
    )
