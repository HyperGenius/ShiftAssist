import { getHolidaysOf } from "japanese-holidays";

import type { SlotType } from "@/types/shiftRequirement";

/** 日本の祝日マップ（YYYY-MM-DD → 祝日名）を取得する */
export function getHolidayMap(year: number, month: number): Map<string, string> {
  const holidays = getHolidaysOf(year);
  const map = new Map<string, string>();
  for (const h of holidays) {
    if (h.month !== month) continue;
    const m = String(h.month).padStart(2, "0");
    const d = String(h.date).padStart(2, "0");
    map.set(`${year}-${m}-${d}`, h.name);
  }
  return map;
}

/** 日本の祝日セット（YYYY-MM-DD 文字列のセット）を取得する */
export function getHolidaySet(year: number, month: number): Set<string> {
  return new Set(getHolidayMap(year, month).keys());
}

/**
 * 月末の祝前日判定に使う拡張祝日セットを取得する。
 * 当月の祝日に加え、翌月1日（月末の翌日）が祝日の場合もセットに含める。
 * これにより isSatPreHolidayDate が月末日付の翌日（翌月初日）が祝日かを正しく判定できる。
 */
export function getExtendedHolidaySet(year: number, month: number): Set<string> {
  const set = getHolidaySet(year, month);

  // 翌月1日の祝日を追加取得する
  const nextYear = month === 12 ? year + 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextMonthHolidays = getHolidaysOf(nextYear);
  for (const h of nextMonthHolidays) {
    if (h.month === nextMonth && h.date === 1) {
      const m = String(h.month).padStart(2, "0");
      const d = String(h.date).padStart(2, "0");
      set.add(`${nextYear}-${m}-${d}`);
    }
  }
  return set;
}

/** 日付が土曜日かどうか */
export function isSaturday(date: Date): boolean {
  return date.getDay() === 6;
}

/** 日付が日曜日かどうか */
export function isSunday(date: Date): boolean {
  return date.getDay() === 0;
}

/** 日付が週末か祝日かどうか */
export function isHoliday(dateStr: string, holidaySet: Set<string>): boolean {
  return holidaySet.has(dateStr);
}

export type DayType = "weekday" | "saturday" | "sunday_holiday";

/** 日付の種別を返す */
export function getDayType(
  date: Date,
  dateStr: string,
  holidaySet: Set<string>,
): DayType {
  if (isSaturday(date)) return "saturday";
  if (isSunday(date) || isHoliday(dateStr, holidaySet)) return "sunday_holiday";
  return "weekday";
}

/** 日付種別からデフォルトのスロットタイプ配列を返す */
export function getDefaultSlotTypes(dayType: DayType): SlotType[] {
  switch (dayType) {
    case "weekday":
      return ["weekday_night"];
    case "saturday":
      return ["sat_day", "sat_night"];
    case "sunday_holiday":
      return ["sun_hol_day", "sun_hol_night"];
  }
}

/** YYYY-MM-DD 文字列を Date に変換する */
export function parseDateStr(dateStr: string): Date {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Date を YYYY-MM-DD 文字列に変換する */
export function toDateStr(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** 指定月の全日付（Date[]）を返す */
export function getMonthDates(year: number, month: number): Date[] {
  const dates: Date[] = [];
  const date = new Date(year, month - 1, 1);
  while (date.getMonth() === month - 1) {
    dates.push(new Date(date));
    date.setDate(date.getDate() + 1);
  }
  return dates;
}

/** カレンダーグリッド用の日付配列（先頭を日曜始まりにパディング）を返す */
export function getCalendarGrid(year: number, month: number): (Date | null)[] {
  const dates = getMonthDates(year, month);
  const firstDay = dates[0].getDay(); // 0=日, 1=月, ..., 6=土
  const grid: (Date | null)[] = [];
  for (let i = 0; i < firstDay; i++) {
    grid.push(null);
  }
  for (const d of dates) {
    grid.push(d);
  }
  // 6列になるよう末尾をパディング
  while (grid.length % 7 !== 0) {
    grid.push(null);
  }
  return grid;
}

/**
 * 指定された日付が「土曜・祝前日」かどうかを判定する。
 * - 翌日が土曜日 or 祝日
 * - かつ自身が平日（土曜・日曜・祝日でない）
 */
export function isSatPreHolidayDate(
  dateStr: string,
  holidayDates: Set<string>,
): boolean {
  const date = parseDateStr(dateStr);
  const day = date.getDay(); // 0=日, 1=月, ..., 6=土

  // 自身が土曜・日曜・祝日の場合は対象外
  if (day === 0 || day === 6 || holidayDates.has(dateStr)) {
    return false;
  }

  // 翌日の日付文字列を計算
  const nextDate = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1);
  const nextDateStr = toDateStr(nextDate);
  const nextDay = nextDate.getDay();

  // 翌日が土曜または祝日
  return nextDay === 6 || holidayDates.has(nextDateStr);
}
