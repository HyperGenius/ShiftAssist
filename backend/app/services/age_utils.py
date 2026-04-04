# backend/app/services/age_utils.py
"""年齢計算ユーティリティ.

シフト対象月の初日時点での年齢を計算するためのユーティリティ関数を提供する。
"""

from datetime import date


def calculate_age_at(birth_date: date, reference_date: date) -> int:
    """指定された基準日時点の年齢を計算する.

    Args:
        birth_date: 生年月日。
        reference_date: 年齢計算の基準日。

    Returns:
        基準日時点の年齢（歳）。
    """
    age = reference_date.year - birth_date.year
    # 基準日がまだ誕生日を迎えていない場合は1を引く
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def is_aged_60_or_over(birth_date: date, reference_date: date) -> bool:
    """基準日時点で60歳以上かどうかを判定する.

    Args:
        birth_date: 生年月日。
        reference_date: 判定基準日（シフト対象月の初日を想定）。

    Returns:
        60歳以上の場合True、それ以外はFalse。
    """
    return calculate_age_at(birth_date, reference_date) >= 60
