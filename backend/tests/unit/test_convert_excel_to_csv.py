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
# classify_category
# ---------------------------------------------------------------------------


class TestClassifyCategory:
    """classify_category のテスト."""

    def test_yasoku_detected(self) -> None:
        """'宿直' を含む文字列は _CATEGORY_YASOKU を返す（全角スペース混入も許容）."""
        assert script.classify_category("宿\u3000直") == script._CATEGORY_YASOKU  # 全角スペースありも検出
        assert script.classify_category("宿直") == script._CATEGORY_YASOKU
        assert script.classify_category("宿\u3000\u3000直") == script._CATEGORY_YASOKU  # 二重スペースも検出

    def test_sat_detected(self) -> None:
        """'土曜当番' を含む文字列は _CATEGORY_SAT を返す."""
        assert script.classify_category("土曜当番") == script._CATEGORY_SAT

    def test_hol_detected(self) -> None:
        """'祝日直' を含む文字列は _CATEGORY_HOL を返す."""
        assert script.classify_category("休・祝日直") == script._CATEGORY_HOL

    def test_unknown_returns_none(self) -> None:
        """不明な文字列は None を返す."""
        assert script.classify_category("その他") is None

    def test_empty_returns_none(self) -> None:
        """空文字は None を返す."""
        assert script.classify_category("") is None


# ---------------------------------------------------------------------------
# determine_slot_type
# ---------------------------------------------------------------------------


class TestDetermineSlotType:
    """determine_slot_type のテスト."""

    # 宿直
    def test_yasoku_weekday_returns_weekday_night(self) -> None:
        """宿直 + 平日 -> weekday_night."""
        d = date(2026, 4, 1)  # 水曜
        result = script.determine_slot_type(script._CATEGORY_YASOKU, d, False, False)
        assert result == SlotTypeEnum.weekday_night

    def test_yasoku_saturday_returns_sat_night(self) -> None:
        """宿直 + 土曜 -> sat_night."""
        d = date(2026, 4, 4)  # 土曜
        result = script.determine_slot_type(script._CATEGORY_YASOKU, d, False, False)
        assert result == SlotTypeEnum.sat_night

    def test_yasoku_sunday_returns_sun_hol_night(self) -> None:
        """宿直 + 日曜 -> sun_hol_night."""
        d = date(2026, 4, 5)  # 日曜
        result = script.determine_slot_type(script._CATEGORY_YASOKU, d, False, False)
        assert result == SlotTypeEnum.sun_hol_night

    def test_yasoku_holiday_weekday_returns_sun_hol_night(self) -> None:
        """宿直 + 祝日（平日）-> sun_hol_night."""
        d = date(2026, 4, 1)  # 水曜だが祝日扱いと仮定
        result = script.determine_slot_type(script._CATEGORY_YASOKU, d, True, False)
        assert result == SlotTypeEnum.sun_hol_night

    def test_yasoku_long_holiday_returns_long_hol_night(self) -> None:
        """宿直 + 長期連休 -> long_hol_night."""
        d = date(2026, 5, 3)  # GW
        result = script.determine_slot_type(script._CATEGORY_YASOKU, d, True, True)
        assert result == SlotTypeEnum.long_hol_night

    # 土曜当番
    def test_sat_saturday_returns_sat_day(self) -> None:
        """土曜当番 + 土曜 -> sat_day."""
        d = date(2026, 4, 4)  # 土曜
        result = script.determine_slot_type(script._CATEGORY_SAT, d, False, False)
        assert result == SlotTypeEnum.sat_day

    def test_sat_non_saturday_returns_none(self) -> None:
        """土曜当番 + 平日 -> None（対象外）."""
        d = date(2026, 4, 1)  # 水曜
        result = script.determine_slot_type(script._CATEGORY_SAT, d, False, False)
        assert result is None

    # 休・祝日直
    def test_hol_sunday_returns_sun_hol_day(self) -> None:
        """休・祝日直 + 日曜 -> sun_hol_day."""
        d = date(2026, 4, 5)  # 日曜
        result = script.determine_slot_type(script._CATEGORY_HOL, d, False, False)
        assert result == SlotTypeEnum.sun_hol_day

    def test_hol_holiday_returns_sun_hol_day(self) -> None:
        """休・祝日直 + 祝日 -> sun_hol_day."""
        d = date(2026, 4, 1)  # 水曜だが祝日扱い
        result = script.determine_slot_type(script._CATEGORY_HOL, d, True, False)
        assert result == SlotTypeEnum.sun_hol_day

    def test_hol_long_holiday_returns_long_hol_day(self) -> None:
        """休・祝日直 + 長期連休 -> long_hol_day."""
        d = date(2026, 5, 3)  # GW
        result = script.determine_slot_type(script._CATEGORY_HOL, d, True, True)
        assert result == SlotTypeEnum.long_hol_day

    def test_hol_weekday_not_holiday_returns_none(self) -> None:
        """休・祝日直 + 平日（非祝日）-> None（対象外）."""
        d = date(2026, 4, 1)  # 水曜・非祝日
        result = script.determine_slot_type(script._CATEGORY_HOL, d, False, False)
        assert result is None

    def test_unknown_category_returns_none(self) -> None:
        """未知のカテゴリ -> None."""
        d = date(2026, 4, 1)
        result = script.determine_slot_type("unknown", d, False, False)
        assert result is None


# ---------------------------------------------------------------------------
# parse_header
# ---------------------------------------------------------------------------


class TestParseHeader:
    """parse_header のテスト."""

    def _make_df(self, row0: list, row1: list) -> pd.DataFrame:
        """テスト用データフレームを生成する."""
        import pandas as pd

        return pd.DataFrame([row0, row1])

    def test_basic_header_detected(self) -> None:
        """宿直・土曜当番・休祝日直の氏名列を正しく検出する."""
        row0 = [
            "日", "曜",
            "宿直", "", "", "", "", "", "", "", "",  # cols 2-10
            "土曜当番", "",  "",                     # cols 11-13
            "休・祝日直", "", "",                    # cols 14-16
        ]
        row1 = [
            "", "",
            "回数", "氏名", "交替者名",             # cols 2-4  (宿直 shift1)
            "回数", "氏名", "交替者名",             # cols 5-7  (宿直 shift2)
            "回数", "氏名", "交替者名",             # cols 8-10 (宿直 shift3)
            "回数", "氏名", "交替者名",             # cols 11-13 (土曜当番)
            "回数", "氏名", "交替者名",             # cols 14-16 (休祝日直)
        ]
        df = self._make_df(row0, row1)
        result = script.parse_header(df)

        # 宿直の氏名列
        assert result.get(3) == script._CATEGORY_YASOKU
        assert result.get(6) == script._CATEGORY_YASOKU
        assert result.get(9) == script._CATEGORY_YASOKU
        # 土曜当番の氏名列
        assert result.get(12) == script._CATEGORY_SAT
        # 休祝日直の氏名列
        assert result.get(15) == script._CATEGORY_HOL

    def test_no_meishi_columns_returns_empty(self) -> None:
        """氏名列がない場合は空辞書を返す."""
        row0 = ["日", "曜", "宿直"]
        row1 = ["", "", "回数"]  # 氏名なし
        df = self._make_df(row0, row1)
        result = script.parse_header(df)
        assert result == {}

    def test_skips_first_two_columns(self) -> None:
        """最初の 2 列（日・曜）はスキップする."""
        row0 = ["氏名", "氏名", "宿直"]  # 最初の 2 列に「氏名」があってもスキップ
        row1 = ["氏名", "氏名", "氏名"]
        df = self._make_df(row0, row1)
        result = script.parse_header(df)
        # col 2 は宿直カテゴリ内の氏名
        assert 0 not in result
        assert 1 not in result
        assert result.get(2) == script._CATEGORY_YASOKU


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
