# backend/tests/unit/test_convert_excel_to_csv.py
"""convert_excel_to_csv スクリプトの純関数に対する単体テスト.

外部依存（DB, ファイル I/O）を持たない関数のみをテスト対象とする。
"""

import sys
import os
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

# scripts/ ディレクトリをパスに追加してスクリプトをインポート可能にする
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

import convert_excel_to_csv as script  # noqa: E402
from app.models.models import SlotTypeEnum  # noqa: E402


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    """normalize_name のテスト."""

    def test_removes_half_width_spaces(self) -> None:
        """半角スペースを除去する."""
        assert script.normalize_name("山田 太郎") == "山田太郎"

    def test_removes_full_width_spaces(self) -> None:
        """全角スペースを除去する."""
        assert script.normalize_name("山田\u3000太郎") == "山田太郎"

    def test_removes_mixed_spaces(self) -> None:
        """全角・半角スペース混在でも除去する."""
        assert script.normalize_name("保安１課\u3000山田 太郎") == "保安１課山田太郎"

    def test_empty_string_stays_empty(self) -> None:
        """空文字は空文字のまま."""
        assert script.normalize_name("") == ""


# ---------------------------------------------------------------------------
# to_str
# ---------------------------------------------------------------------------


class TestToStr:
    """to_str のテスト."""

    def test_none_returns_empty(self) -> None:
        """None を空文字に変換する."""
        assert script.to_str(None) == ""

    def test_float_nan_returns_empty(self) -> None:
        """float NaN を空文字に変換する."""
        assert script.to_str(float("nan")) == ""

    def test_nan_string_returns_empty(self) -> None:
        """文字列 'nan' を空文字に変換する."""
        assert script.to_str("nan") == ""

    def test_number_converts_to_string(self) -> None:
        """数値を文字列に変換する."""
        assert script.to_str(1) == "1"

    def test_string_stripped(self) -> None:
        """文字列は前後の空白を除去する."""
        assert script.to_str("  hello  ") == "hello"


# ---------------------------------------------------------------------------
# extract_name_from_cell
# ---------------------------------------------------------------------------


class TestExtractNameFromCell:
    """extract_name_from_cell のテスト."""

    def test_plain_name(self) -> None:
        """純粋な氏名をそのまま返す."""
        assert script.extract_name_from_cell("山田 太郎") == "山田 太郎"

    def test_dept_plus_name(self) -> None:
        """部署名＋氏名でもそのまま返す（分割しない）."""
        assert script.extract_name_from_cell("保安１課\u3000山田\u3000太郎") == "保安１課\u3000山田\u3000太郎"

    def test_removes_round_number_symbols(self) -> None:
        """①②等の回数記号を除去する."""
        assert script.extract_name_from_cell("①山田 太郎") == "山田 太郎"
        assert script.extract_name_from_cell("②") == ""

    def test_none_returns_empty(self) -> None:
        """None は空文字を返す."""
        assert script.extract_name_from_cell(None) == ""

    def test_nan_float_returns_empty(self) -> None:
        """float NaN は空文字を返す."""
        assert script.extract_name_from_cell(float("nan")) == ""

    def test_whitespace_only_returns_empty(self) -> None:
        """空白のみは空文字を返す."""
        assert script.extract_name_from_cell("   ") == ""


# ---------------------------------------------------------------------------
# determine_slot_type
# ---------------------------------------------------------------------------


class TestDetermineSlotType:
    """determine_slot_type のテスト."""

    # 1回目・2回目 (occurrence_idx=0,1)
    def test_first_occurrence_weekday_returns_weekday_night(self) -> None:
        """1回目 + 平日 -> weekday_night."""
        d = date(2026, 4, 1)  # 水曜
        result = script.determine_slot_type(0, d, False, False)
        assert result == SlotTypeEnum.weekday_night

    def test_second_occurrence_weekday_returns_weekday_night(self) -> None:
        """2回目 + 平日 -> weekday_night."""
        d = date(2026, 4, 1)  # 水曜
        result = script.determine_slot_type(1, d, False, False)
        assert result == SlotTypeEnum.weekday_night

    def test_first_occurrence_saturday_returns_sat_day(self) -> None:
        """1回目 + 土曜 -> sat_day."""
        d = date(2026, 4, 4)  # 土曜
        result = script.determine_slot_type(0, d, False, False)
        assert result == SlotTypeEnum.sat_day

    def test_first_occurrence_sunday_returns_sun_hol_day(self) -> None:
        """1回目 + 日曜 -> sun_hol_day."""
        d = date(2026, 4, 5)  # 日曜
        result = script.determine_slot_type(0, d, False, False)
        assert result == SlotTypeEnum.sun_hol_day

    def test_first_occurrence_holiday_weekday_returns_sun_hol_day(self) -> None:
        """1回目 + 祝日（平日）-> sun_hol_day."""
        d = date(2026, 4, 1)  # 水曜だが祝日扱いと仮定
        result = script.determine_slot_type(0, d, True, False)
        assert result == SlotTypeEnum.sun_hol_day

    def test_first_occurrence_long_holiday_returns_long_hol_day(self) -> None:
        """1回目 + 長期連休 -> long_hol_day."""
        d = date(2026, 5, 3)  # GW
        result = script.determine_slot_type(0, d, True, True)
        assert result == SlotTypeEnum.long_hol_day

    # 3回目・4回目 (occurrence_idx=2,3)
    def test_third_occurrence_saturday_returns_sat_night(self) -> None:
        """3回目 + 土曜 -> sat_night."""
        d = date(2026, 4, 4)  # 土曜
        result = script.determine_slot_type(2, d, False, False)
        assert result == SlotTypeEnum.sat_night

    def test_fourth_occurrence_saturday_returns_sat_night(self) -> None:
        """4回目 + 土曜 -> sat_night."""
        d = date(2026, 4, 4)  # 土曜
        result = script.determine_slot_type(3, d, False, False)
        assert result == SlotTypeEnum.sat_night

    def test_third_occurrence_sunday_returns_sun_hol_night(self) -> None:
        """3回目 + 日曜 -> sun_hol_night."""
        d = date(2026, 4, 5)  # 日曜
        result = script.determine_slot_type(2, d, False, False)
        assert result == SlotTypeEnum.sun_hol_night

    def test_third_occurrence_holiday_returns_sun_hol_night(self) -> None:
        """3回目 + 祝日（平日）-> sun_hol_night."""
        d = date(2026, 4, 1)  # 水曜だが祝日扱い
        result = script.determine_slot_type(2, d, True, False)
        assert result == SlotTypeEnum.sun_hol_night

    def test_third_occurrence_long_holiday_returns_long_hol_night(self) -> None:
        """3回目 + 長期連休 -> long_hol_night."""
        d = date(2026, 5, 3)  # GW
        result = script.determine_slot_type(2, d, True, True)
        assert result == SlotTypeEnum.long_hol_night

    def test_third_occurrence_weekday_returns_none(self) -> None:
        """3回目 + 平日 -> None（対象外）."""
        d = date(2026, 4, 1)  # 水曜
        result = script.determine_slot_type(2, d, False, False)
        assert result is None

# ---------------------------------------------------------------------------
# parse_header
# ---------------------------------------------------------------------------


class TestParseHeader:
    """parse_header のテスト."""

    def _make_df(self, rows: list) -> "pd.DataFrame":
        """テスト用データフレームを生成する."""
        import pandas as pd
        return pd.DataFrame(rows)

    def test_basic_header_detected(self) -> None:
        """3行目の氏名列インデックスをリストで検出する."""
        row0 = ["skip1", "skip2", "skip3"]
        row1 = ["skip1", "skip2", "skip3"]
        row2 = ["日", "曜日", "回数", "氏名", "交替者名", "回数", "氏名", "交替者名", "回数", "氏名"]
        df = self._make_df([row0, row1, row2])
        result = script.parse_header(df)
        assert result == [3, 6, 9]

    def test_no_meishi_columns_returns_empty(self) -> None:
        """氏名列がない場合は空リストを返す."""
        row0 = ["日", "曜", "宿直"]
        row1 = ["", "", ""]
        row2 = ["日", "曜", "回数"]  # 氏名なし
        df = self._make_df([row0, row1, row2])
        result = script.parse_header(df)
        assert result == []

    def test_less_than_3_rows_returns_empty(self) -> None:
        """3行未満の場合は空リストを返す."""
        row0 = ["日", "曜", "氏名"]
        df = self._make_df([row0])
        result = script.parse_header(df)
        assert result == []

    def test_occurrence_order_preserved(self) -> None:
        """氏名列が左から順に収集されることを確認する."""
        row0 = ["x"] * 6
        row1 = ["x"] * 6
        row2 = ["日", "氏名", "回数", "氏名", "回数", "氏名"]
        df = self._make_df([row0, row1, row2])
        result = script.parse_header(df)
        assert result == [1, 3, 5]

# ---------------------------------------------------------------------------
# build_worker_cache
# ---------------------------------------------------------------------------


class TestBuildWorkerCache:
    """build_worker_cache のテスト."""

    def _make_worker(self, name: str, employee_code: str | None, uuid_str: str) -> MagicMock:
        """テスト用 Worker モックを生成する."""
        w = MagicMock()
        w.name = name
        w.employee_code = employee_code
        w.id = uuid_str
        return w

    def test_employee_code_used_when_available(self) -> None:
        """employee_code がある場合はそれを識別子に使う."""
        workers = [self._make_worker("山田 太郎", "1234567", "some-uuid")]
        cache = script.build_worker_cache(workers)
        assert cache.get("山田太郎") == "1234567"

    def test_uuid_used_when_no_employee_code(self) -> None:
        """employee_code が None の場合は UUID 文字列を使う."""
        workers = [self._make_worker("鈴木 一郎", None, "uuid-abc")]
        cache = script.build_worker_cache(workers)
        assert cache.get("鈴木一郎") == "uuid-abc"

    def test_name_normalized(self) -> None:
        """名前のスペースを除去して正規化する."""
        workers = [self._make_worker("高橋\u3000三郎", "9876543", "x")]
        cache = script.build_worker_cache(workers)
        assert "高橋三郎" in cache

    def test_empty_list_returns_empty_cache(self) -> None:
        """空リストは空辞書を返す."""
        assert script.build_worker_cache([]) == {}


# ---------------------------------------------------------------------------
# lookup_worker_id
# ---------------------------------------------------------------------------


class TestLookupWorkerId:
    """lookup_worker_id のテスト."""

    def test_exact_match(self) -> None:
        """正規化後の完全一致で識別子を返す."""
        cache = {"山田太郎": "1234567"}
        assert script.lookup_worker_id("山田太郎", cache) == "1234567"

    def test_endswith_match_strips_dept(self) -> None:
        """部署名プレフィックスを除いた末尾一致で識別子を返す."""
        cache = {"山田太郎": "1234567"}
        # 全角スペース区切りの「部署名　氏名」形式
        assert script.lookup_worker_id("保安１課\u3000山田\u3000太郎", cache) == "1234567"

    def test_endswith_longest_match_wins(self) -> None:
        """複数候補がある場合、最長一致を優先する."""
        cache = {
            "太郎": "wrong",
            "山田太郎": "correct",
        }
        assert script.lookup_worker_id("保安１課\u3000山田\u3000太郎", cache) == "correct"

    def test_split_two_tokens_fallback(self) -> None:
        """スペース分割の末尾 2 トークン結合で一致する場合."""
        cache = {"山田太郎": "1234567"}
        assert script.lookup_worker_id("保安１課 山田 太郎", cache) == "1234567"

    def test_split_one_token_fallback(self) -> None:
        """スペース分割の末尾 1 トークンで一致する場合."""
        cache = {"太郎": "9999"}
        assert script.lookup_worker_id("保安１課 山田 太郎", cache) == "9999"

    def test_not_found_returns_none(self) -> None:
        """一致なしの場合は None を返す."""
        cache = {"鈴木花子": "0000001"}
        assert script.lookup_worker_id("山田 太郎", cache) is None

    def test_empty_cell_returns_none(self) -> None:
        """空のセル値は None を返す."""
        cache = {"山田太郎": "1234567"}
        assert script.lookup_worker_id("", cache) is None


# ---------------------------------------------------------------------------
# convert 出力形式（新フォーマット：最初の2行をスキップ、3行目がヘッダー）
# ---------------------------------------------------------------------------


class TestConvertOutputFormat:
    """convert 関数の出力 CSV フォーマットと SlotType 判定を検証する."""

    def _make_input_csv(self, tmp_path, filename: str, data_rows: list) -> str:
        """新フォーマットの入力 CSV を作成するヘルパー.

        row0, row1 はスキップ行（3行目のヘッダー行と同じ列数にパディング）。
        row2 が固定ヘッダー行、row3 以降がデータ行。
        """
        import csv

        # 全行の列数を揃えるために最大列数でパディング
        num_cols = max(len(r) for r in data_rows)
        skip_row = [""] * num_cols
        all_rows = [
            skip_row,  # row 0
            skip_row,  # row 1
        ] + data_rows
        path = tmp_path / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(all_rows)
        return str(path)

    def test_required_count_in_fieldnames(self, tmp_path: "pathlib.Path") -> None:  # type: ignore[name-defined]
        """正常系: 出力 CSV に required_count 列が含まれる."""
        import csv

        # 新フォーマット: 3行目がヘッダー（日, 曜, 回数, 氏名, 交替者名）
        # 4行目以降がデータ（2026-04-01 は水曜 = 平日）
        input_path = self._make_input_csv(tmp_path, "input.csv", [
            ["日", "曜", "回数", "氏名", "交替者名"],  # row2 (header)
            ["1", "月", "1", "山田太郎", ""],           # row3 (data)
        ])
        output_path = str(tmp_path / "output.csv")

        script.convert(
            input_path=input_path,
            output_path=output_path,
            year_month="2026-04",
            tenant_id=None,
            db_url=None,
        )

        with open(output_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) > 0, "出力行が存在すること"
        assert "required_count" in rows[0], "required_count 列が存在すること"

    def test_required_count_value_matches_worker_count(
        self, tmp_path: "pathlib.Path"  # type: ignore[name-defined]
    ) -> None:
        """正常系: required_count の値がワーカー数と一致する."""
        import csv

        # 1回目・2回目の氏名列（平日 -> weekday_night）に2名アサイン
        input_path = self._make_input_csv(tmp_path, "input2.csv", [
            ["日", "曜", "回数", "氏名", "交替者名", "回数", "氏名"],  # row2 (header)
            ["1", "月", "1", "山田太郎", "", "1", "鈴木花子"],           # row3 (data, 2026-04-01=水曜)
        ])
        output_path = str(tmp_path / "output2.csv")

        script.convert(
            input_path=input_path,
            output_path=output_path,
            year_month="2026-04",
            tenant_id=None,
            db_url=None,
        )

        with open(output_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        wn_rows = [r for r in rows if r["slot_type"] == "weekday_night"]
        assert wn_rows, "weekday_night 行が存在すること"
        assert wn_rows[0]["required_count"] == "2"

    def test_weekday_first_occurrence_is_weekday_night(
        self, tmp_path: "pathlib.Path"  # type: ignore[name-defined]
    ) -> None:
        """平日の1回目・2回目の氏名が weekday_night として出力される."""
        import csv

        input_path = self._make_input_csv(tmp_path, "input3.csv", [
            ["日", "曜", "回数", "氏名"],  # row2 (header)
            ["1", "月", "1", "山田太郎"],  # row3 (data, 2026-04-01=水曜=平日)
        ])
        output_path = str(tmp_path / "output3.csv")

        script.convert(
            input_path=input_path,
            output_path=output_path,
            year_month="2026-04",
            tenant_id=None,
            db_url=None,
        )

        with open(output_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert any(r["slot_type"] == "weekday_night" for r in rows),             "weekday_night 行が出力 CSV に存在すること"

    def test_saturday_third_occurrence_is_sat_night(
        self, tmp_path: "pathlib.Path"  # type: ignore[name-defined]
    ) -> None:
        """土曜日の3回目・4回目の氏名が sat_night として出力される."""
        import csv

        # 2026-04-04 は土曜
        # 3回目の氏名列（occurrence_idx=2）-> sat_night
        input_path = self._make_input_csv(tmp_path, "input4.csv", [
            ["日", "曜", "回数", "氏名", "交替者名", "回数", "氏名", "交替者名", "回数", "氏名"],
            ["4", "土", "1", "山田太郎", "", "1", "鈴木花子", "", "1", "田中三郎"],
        ])
        output_path = str(tmp_path / "output4.csv")

        script.convert(
            input_path=input_path,
            output_path=output_path,
            year_month="2026-04",
            tenant_id=None,
            db_url=None,
        )

        with open(output_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        sat_night_rows = [r for r in rows if r["slot_type"] == "sat_night"]
        assert sat_night_rows, "sat_night 行が出力 CSV に存在すること"
        assert sat_night_rows[0]["worker_id_1"] == "田中三郎"

    def test_sunday_third_occurrence_is_sun_hol_night(
        self, tmp_path: "pathlib.Path"  # type: ignore[name-defined]
    ) -> None:
        """日曜日の3回目・4回目の氏名が sun_hol_night として出力される."""
        import csv

        # 2026-04-05 は日曜
        # 3回目の氏名列（occurrence_idx=2）-> sun_hol_night
        input_path = self._make_input_csv(tmp_path, "input5.csv", [
            ["日", "曜", "回数", "氏名", "交替者名", "回数", "氏名", "交替者名", "回数", "氏名"],
            ["5", "日", "1", "山田太郎", "", "1", "鈴木花子", "", "1", "田中三郎"],
        ])
        output_path = str(tmp_path / "output5.csv")

        script.convert(
            input_path=input_path,
            output_path=output_path,
            year_month="2026-04",
            tenant_id=None,
            db_url=None,
        )

        with open(output_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        night_rows = [r for r in rows if r["slot_type"] == "sun_hol_night"]
        assert night_rows, "sun_hol_night 行が出力 CSV に存在すること"
        assert night_rows[0]["worker_id_1"] == "田中三郎"
