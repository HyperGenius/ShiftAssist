# backend/tests/unit/test_age_utils.py
"""age_utils モジュールの単体テスト."""

from datetime import date

import pytest

from app.services.age_utils import calculate_age_at, is_aged_60_or_over


class TestCalculateAgeAt:
    """calculate_age_at の単体テスト."""

    def test_exact_birthday(self) -> None:
        """正常系: 誕生日当日の年齢が正しく計算される."""
        birth_date = date(1966, 4, 1)
        reference_date = date(2026, 4, 1)
        assert calculate_age_at(birth_date, reference_date) == 60

    def test_before_birthday_in_year(self) -> None:
        """正常系: 誕生日前は1歳引かれる."""
        birth_date = date(1966, 6, 1)
        reference_date = date(2026, 4, 1)
        assert calculate_age_at(birth_date, reference_date) == 59

    def test_after_birthday_in_year(self) -> None:
        """正常系: 誕生日後は正しい年齢が返る."""
        birth_date = date(1966, 1, 1)
        reference_date = date(2026, 4, 1)
        assert calculate_age_at(birth_date, reference_date) == 60

    def test_leap_year_birthday(self) -> None:
        """正常系: うるう年生まれの年齢計算."""
        birth_date = date(1968, 2, 29)
        reference_date = date(2026, 3, 1)
        # 2026年は2月29日がないため、3月1日時点では58歳
        assert calculate_age_at(birth_date, reference_date) == 58


class TestIsAged60OrOver:
    """is_aged_60_or_over の単体テスト."""

    def test_exactly_60(self) -> None:
        """正常系: ちょうど60歳の場合はTrue."""
        birth_date = date(1966, 4, 1)
        reference_date = date(2026, 4, 1)
        assert is_aged_60_or_over(birth_date, reference_date) is True

    def test_61_years_old(self) -> None:
        """正常系: 61歳の場合はTrue."""
        birth_date = date(1965, 1, 1)
        reference_date = date(2026, 4, 1)
        assert is_aged_60_or_over(birth_date, reference_date) is True

    def test_59_years_old(self) -> None:
        """正常系: 59歳の場合はFalse."""
        birth_date = date(1967, 4, 2)
        reference_date = date(2026, 4, 1)
        assert is_aged_60_or_over(birth_date, reference_date) is False

    def test_just_before_60th_birthday(self) -> None:
        """正常系: 60歳の誕生日前日はFalse."""
        birth_date = date(1966, 4, 2)
        reference_date = date(2026, 4, 1)
        assert is_aged_60_or_over(birth_date, reference_date) is False
