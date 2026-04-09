#!/usr/bin/env python3
"""過去シフトExcel/CSVをShiftAssistインポート用CSVへ変換するスクリプト.

使用方法::

    python scripts/convert_excel_to_csv.py \\
        --input path/to/input.csv \\
        --output path/to/output.csv \\
        --year-month 2026-04

入力ファイルの形式:
    1行目: 固定ヘッダー行（日, 曜日, 回数, 氏名, ... の繰り返し）
    以降:  データ行（1列目=日、2列目=曜、以降=各シフト担当者情報）

    「氏名」列の左からの出現順によりシフト種別を判定する:
    - 1回目・2回目: 平日=宿直, 土曜=昼間, 日祝=昼間
    - 3回目・4回目: 平日=対象外, 土曜=夜間, 日祝=夜間

出力ファイルの形式（ShiftAssistインポート形式）::

    date,slot_type,required_count,worker_id_1,worker_id_2,...
    2026-04-01,weekday_night,2,1234567,2468013
    ...

``required_count`` 列にはその枠にアサインされた人数が記録される。
これは過去データの ``shift_requirements.required_headcount`` としてそのまま利用可能。

ワーカー識別子には、DBに ``employee_code`` が登録されていればその値を、
未登録の場合はワーカーUUID文字列を使用する。
"""

import argparse
import calendar
import csv
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from typing import Any

import jpholiday
import pandas as pd

# backend/ ディレクトリをパスに追加して app モジュールを参照できるようにする
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.models import SlotTypeEnum, TenantHoliday, Worker  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 純関数ユーティリティ（テスト可能）
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """スペース（全角・半角）を除去して名前を正規化する.

    Args:
        name: 正規化前の名前文字列。

    Returns:
        全角・半角スペースを除去した文字列。
    """
    return re.sub(r"[\s\u3000]", "", name)


def to_str(val: Any) -> str:
    """任意の値を文字列に変換し、NaN / None は空文字を返す.

    Args:
        val: 変換対象の値。

    Returns:
        文字列表現（NaN/Noneの場合は空文字）。
    """
    if val is None:
        return ""
    if isinstance(val, float) and (val != val):  # NaN check without math import
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def extract_name_from_cell(cell_value: Any) -> str:
    """セル値から氏名候補文字列を抽出する.

    セル値「保安１課　山田　太郎」のように部署名＋氏名が含まれる場合も、
    そのまま正規化せずに返す（マッチングは呼び出し側で行う）。
    回数記号（①②③等）は除去する。

    Args:
        cell_value: セルの値。

    Returns:
        氏名候補文字列（空の場合は空文字）。
    """
    cell_str = to_str(cell_value)
    if not cell_str:
        return ""
    # ①②③等の回数記号を除去
    cell_str = re.sub(r"[①-⑳]", "", cell_str).strip()
    return cell_str


def determine_slot_type(
    occurrence_idx: int,
    shift_date: date,
    is_holiday: bool,
    is_long_holiday: bool,
) -> SlotTypeEnum | None:
    """出現順と日付情報から SlotTypeEnum を決定する.

    氏名列の左からの出現順（0-indexed）によってシフト種別を判定する。

    - 0回目・1回目（1回目・2回目）の氏名列:
        - 長期連休 -> long_hol_day
        - 土曜 -> sat_day
        - 日曜または祝日 -> sun_hol_day
        - 平日 -> weekday_night
    - 2回目・3回目（3回目・4回目）の氏名列:
        - 長期連休 -> long_hol_night
        - 土曜 -> sat_night
        - 日曜または祝日 -> sun_hol_night
        - 平日 -> None（対象外）

    Args:
        occurrence_idx: 氏名列の出現順（0-indexed）。
        shift_date: 対象日付。
        is_holiday: 祝日フラグ（土曜を除く）。
        is_long_holiday: 長期連休フラグ（GW・年末年始等）。

    Returns:
        対応する SlotTypeEnum。対象外の場合は None。
    """
    weekday = shift_date.weekday()  # 0=月曜 … 5=土曜, 6=日曜
    is_saturday = weekday == 5
    is_sunday = weekday == 6

    if occurrence_idx <= 1:
        # 1回目・2回目: 昼間枠または宿直
        if is_long_holiday:
            return SlotTypeEnum.long_hol_day
        if is_saturday:
            return SlotTypeEnum.sat_day
        if is_sunday or is_holiday:
            return SlotTypeEnum.sun_hol_day
        return SlotTypeEnum.weekday_night

    # 3回目・4回目: 夜間枠
    if is_long_holiday:
        return SlotTypeEnum.long_hol_night
    if is_saturday:
        return SlotTypeEnum.sat_night
    if is_sunday or is_holiday:
        return SlotTypeEnum.sun_hol_night
    # 平日の3回目・4回目は対象外
    return None


def parse_header(df: pd.DataFrame) -> list[int]:
    """データフレームの1行目（インデックス0）から氏名列インデックスのリストを返す.

    1行目を固定ヘッダー行として扱う。
    「氏名」という文字列が含まれる列のインデックスを左から順に収集する。
    各インデックスのリスト内位置（0-indexed）が出現順として
    ``determine_slot_type`` の ``occurrence_idx`` に対応する。

    Args:
        df: ヘッダーなしで読み込んだデータフレーム。

    Returns:
        「氏名」列インデックスのリスト（出現順）。
    """
    if len(df) < 1:
        return []
    header_row = df.iloc[0]
    return [
        col_idx
        for col_idx in range(len(header_row))
        if to_str(header_row.iloc[col_idx]) == "氏名"
    ]


def build_worker_cache(workers: list[Any]) -> dict[str, str]:
    """Worker オブジェクトのリストから正規化名前 -> 識別子 マッピングを構築する.

    識別子は employee_code を優先し、未登録の場合は UUID 文字列を使用する。

    Args:
        workers: Worker ORM オブジェクトのリスト。

    Returns:
        正規化名前 -> 識別子 のマッピング。
    """
    cache: dict[str, str] = {}
    for w in workers:
        normalized = normalize_name(w.name)
        identifier = w.employee_code if w.employee_code else str(w.id)
        cache[normalized] = identifier
    return cache


def lookup_worker_id(
    name_in_cell: str,
    worker_cache: dict[str, str],
) -> str | None:
    """セル値（氏名候補）からワーカー識別子を検索する.

    マッチング手順:
    1. 正規化したセル値でキャッシュを完全一致検索。
    2. 「部署名 + 氏名」形式に備え、セル正規化値がキャッシュ正規化名で
       終端するかを確認（最長一致優先）。
    3. スペース分割の末尾トークン（2トークン結合 / 1トークン）で再試行。

    Args:
        name_in_cell: セルの生の値（部署名＋氏名の可能性あり）。
        worker_cache: 正規化名前 -> 識別子 のマッピング。

    Returns:
        ワーカー識別子（見つからない場合は None）。
    """
    normalized_cell = normalize_name(name_in_cell)
    if not normalized_cell:
        return None

    # 1. 完全一致
    if normalized_cell in worker_cache:
        return worker_cache[normalized_cell]

    # 2. 末尾部分一致（部署名プレフィックスを除く）：長い名前を優先
    candidates: list[tuple[int, str]] = []
    for norm_name, worker_id in worker_cache.items():
        if norm_name and normalized_cell.endswith(norm_name):
            candidates.append((len(norm_name), worker_id))
    if candidates:
        # 最長一致を返す
        return max(candidates, key=lambda x: x[0])[1]

    # 3. スペース分割の末尾トークンで再試行
    parts = re.split(r"[\s\u3000]+", name_in_cell.strip())
    if len(parts) >= 2:
        two_tokens = normalize_name("".join(parts[-2:]))
        if two_tokens in worker_cache:
            return worker_cache[two_tokens]
        one_token = normalize_name(parts[-1])
        if one_token in worker_cache:
            return worker_cache[one_token]

    return None


# ---------------------------------------------------------------------------
# I/O ヘルパー
# ---------------------------------------------------------------------------


def load_input_file(input_path: str) -> pd.DataFrame:
    """CSV または Excel ファイルを読み込み、ヘッダーなしのデータフレームを返す.

    文字コードは UTF-8 (BOM 付き含む) / Shift-JIS を自動判別。

    Args:
        input_path: 読み込むファイルのパス。

    Returns:
        全セルを文字列として保持するデータフレーム。

    Raises:
        SystemExit: 読み込みに失敗した場合。
    """
    ext = os.path.splitext(input_path)[1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(input_path, header=None, dtype=str)
        else:
            # CSV: UTF-8-BOM → UTF-8 → Shift-JIS の順で試みる
            df = None
            for enc in ("utf-8-sig", "utf-8", "shift_jis"):
                try:
                    df = pd.read_csv(
                        input_path,
                        header=None,
                        dtype=str,
                        na_filter=False,
                        encoding=enc,
                    )
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            if df is None:
                raise ValueError("文字コードを判別できませんでした")
    except Exception as exc:
        print(f"❌ 入力ファイルの読み込みに失敗しました: {exc}")
        sys.exit(1)
    return df


def load_holidays_from_db(
    session: Any,
    tenant_id: str,
    year: int,
    month: int,
) -> tuple[set[date], set[date]]:
    """DB から対象年月の祝日セットを取得する.

    Args:
        session: SQLAlchemy セッション。
        tenant_id: テナント ID。
        year: 対象年。
        month: 対象月。

    Returns:
        (holidays: set[date], long_holidays: set[date]) のタプル。
    """
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    db_records = (
        session.query(TenantHoliday)
        .filter(
            TenantHoliday.tenant_id == tenant_id,
            TenantHoliday.date >= start,
            TenantHoliday.date <= end,
        )
        .all()
    )
    holidays: set[date] = set()
    long_holidays: set[date] = set()
    for h in db_records:
        holidays.add(h.date)
        if h.is_long_holiday:
            long_holidays.add(h.date)
    return holidays, long_holidays


def load_holidays_from_jpholiday(year: int, month: int) -> set[date]:
    """jpholiday から対象年月の日本標準祝日セットを取得する.

    Args:
        year: 対象年。
        month: 対象月。

    Returns:
        祝日の date セット。
    """
    result: set[date] = set()
    for h_date, _ in jpholiday.year_holidays(year):
        if h_date.month == month:
            result.add(h_date)
    return result


# ---------------------------------------------------------------------------
# 変換メイン処理
# ---------------------------------------------------------------------------


def convert(
    input_path: str,
    output_path: str,
    year_month: str,
    tenant_id: str | None,
    db_url: str | None,
) -> int:
    """変換処理のメイン関数.

    Args:
        input_path: 入力ファイルパス。
        output_path: 出力 CSV ファイルパス。
        year_month: 対象年月（YYYY-MM 形式）。
        tenant_id: テナント ID（省略可）。
        db_url: DB 接続 URL（省略可、None の場合は DB アクセスなし）。

    Returns:
        出力した行数。
    """
    # 年月パース
    try:
        ym_date = datetime.strptime(year_month, "%Y-%m")
    except ValueError:
        print(f"❌ --year-month の形式が不正です（YYYY-MM 形式が必要）: {year_month}")
        sys.exit(1)
    year = ym_date.year
    month = ym_date.month

    # 入力ファイル読み込み
    print(f"📂 入力ファイルを読み込み中: {input_path}")
    df = load_input_file(input_path)

    if len(df) < 2:
        print("❌ データ行がありません（ヘッダー1行 + データ1行以上が必要）。")
        sys.exit(1)

    # ヘッダー解析（1行目の氏名列インデックスを収集）
    name_col_list = parse_header(df)
    if not name_col_list:
        print("⚠️  氏名列が見つかりませんでした。ヘッダー構造を確認してください。")
        sys.exit(1)
    print(f"✅ 氏名列を検出: {name_col_list}")

    # DB 接続とワーカーキャッシュの構築
    session = None
    worker_cache: dict[str, str] = {}
    holidays: set[date] = set()
    long_holidays: set[date] = set()

    if db_url and tenant_id:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(db_url)
            _SessionLocal = sessionmaker(bind=engine)
            session = _SessionLocal()
            print(f"🔌 DB 接続: テナント '{tenant_id}' のワーカー情報を取得中...")
            db_workers = (
                session.query(Worker).filter(Worker.tenant_id == tenant_id).all()
            )
            worker_cache = build_worker_cache(db_workers)
            print(f"✅ ワーカーキャッシュ構築完了: {len(worker_cache)} 件")

            holidays, long_holidays = load_holidays_from_db(session, tenant_id, year, month)
            if not holidays:
                print("   DB に祝日データがありません。jpholiday でフォールバックします。")
                holidays = load_holidays_from_jpholiday(year, month)
        except Exception as exc:
            print(f"⚠️  DB 接続に失敗しました: {exc}")
            print("   ワーカー名をそのまま出力します（DB なし）。")
            session = None
            holidays = load_holidays_from_jpholiday(year, month)
    else:
        print("⚠️  --tenant-id または DB URL が未指定のため、ワーカー名をそのまま出力します。")
        holidays = load_holidays_from_jpholiday(year, month)

    print(f"📅 祝日 ({year}-{month:02d}): {sorted(holidays) if holidays else '（なし）'}")

    # データ変換
    data_rows = df.iloc[1:].reset_index(drop=True)
    output_rows: list[dict[str, str]] = []
    warn_count = 0

    for _, row in data_rows.iterrows():
        # 1 列目の「日」を取得
        day_val = to_str(row.iloc[0])
        if not day_val:
            continue

        try:
            day_int = int(float(day_val))
        except (ValueError, TypeError):
            print(f"⚠️  日付の解析に失敗しました（値: {day_val!r}）。スキップします。")
            continue

        try:
            shift_date = date(year, month, day_int)
        except ValueError:
            print(f"⚠️  無効な日付 {year}-{month}-{day_int}。スキップします。")
            continue

        is_holiday = shift_date in holidays
        is_long = shift_date in long_holidays

        # カテゴリごとにワーカーを収集
        slot_workers: dict[SlotTypeEnum, list[str]] = defaultdict(list)

        for occurrence_idx, col_idx in enumerate(name_col_list):
            if col_idx >= len(row):
                continue
            cell_val = row.iloc[col_idx]
            name_str = extract_name_from_cell(cell_val)
            if not name_str:
                continue

            slot_type = determine_slot_type(occurrence_idx, shift_date, is_holiday, is_long)
            if slot_type is None:
                continue

            if worker_cache:
                worker_id = lookup_worker_id(name_str, worker_cache)
                if worker_id is None:
                    print(
                        f"⚠️  '{name_str}' に一致するワーカーが見つかりません"
                        f"（{shift_date}）。スキップします。"
                    )
                    warn_count += 1
                    continue
            else:
                # DB 未接続の場合は氏名をそのまま使用
                worker_id = name_str

            if worker_id not in slot_workers[slot_type]:
                slot_workers[slot_type].append(worker_id)

        # 出力行を生成
        for slot_type, worker_ids in slot_workers.items():
            row_dict: dict[str, str] = {
                "date": shift_date.strftime("%Y-%m-%d"),
                "slot_type": slot_type.value,
                "required_count": str(len(worker_ids)),
            }
            for i, wid in enumerate(worker_ids, start=1):
                row_dict[f"worker_id_{i}"] = wid
            output_rows.append(row_dict)

    # 出力列名を動的に構築
    if not output_rows:
        print("⚠️  出力データがありません。")
        if session:
            session.close()
        return 0

    max_workers = max(
        sum(1 for k in r if k.startswith("worker_id_")) for r in output_rows
    )
    fieldnames = ["date", "slot_type", "required_count"] + [
        f"worker_id_{i}" for i in range(1, max_workers + 1)
    ]

    # CSV 書き出し
    print(f"💾 出力ファイルに書き込み中: {output_path}")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row_dict in output_rows:
            writer.writerow(row_dict)

    print(
        f"✅ 変換完了: {len(output_rows)} 行を出力しました"
        f"（警告: {warn_count} 件）。"
    )

    if session:
        session.close()

    return len(output_rows)


# ---------------------------------------------------------------------------
# CLI エントリーポイント
# ---------------------------------------------------------------------------


def main() -> None:
    """コマンドライン引数をパースして convert() を実行する."""
    parser = argparse.ArgumentParser(
        description="過去シフト Excel/CSV を ShiftAssist インポート用 CSV へ変換する。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", required=True, help="入力 CSV または Excel ファイルのパス")
    parser.add_argument("--output", required=True, help="出力 CSV ファイルのパス")
    parser.add_argument(
        "--year-month",
        required=True,
        help="対象年月（YYYY-MM 形式、例: 2026-04）",
    )
    parser.add_argument(
        "--tenant-id",
        default=(
            os.environ.get("TENANT_ID") or os.environ.get("TEST_ORGANIZATION_ID")
        ),
        help=(
            "テナント ID（省略時は環境変数 TENANT_ID / TEST_ORGANIZATION_ID を参照）"
        ),
    )
    args = parser.parse_args()

    db_url = os.environ.get("NEON_DATABASE_URL")
    convert(
        input_path=args.input,
        output_path=args.output,
        year_month=args.year_month,
        tenant_id=args.tenant_id,
        db_url=db_url,
    )


if __name__ == "__main__":
    main()
