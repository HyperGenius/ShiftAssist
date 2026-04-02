// frontend/utils/shiftValidators.ts
// シフトバリデーションのための純粋関数群

import type { CalendarState, SlotType } from "@/types/shiftRequirement";
import type { Worker } from "@/types/worker";
import { parseDateStr } from "@/utils/calendarUtils";

export type ValidationCode =
  | "DAILY_DUPLICATE" // 1人1日1枠: 同日の複数枠への重複アサイン
  | "SAME_DEPARTMENT" // 同じ所属課同士のペア
  | "SKILL_RANK_A" // スキルランクAがペアに含まれない
  | "WORK_INTERVAL" // 中9日未満の勤務間隔
  | "SPECIAL_EMPLOYMENT" // 特別雇用者の枠制限違反
  | "CONSECUTIVE_HOLIDAYS"; // 休日の連続アサイン (Warning)

export type ValidationSeverity = "error" | "warning";

export interface ValidationViolation {
  code: ValidationCode;
  severity: ValidationSeverity;
  message: string;
  workerIds: string[];
}

/** 特定のスロットタイプが平日夜間以外（休日昼・夜、長期連休）かどうか */
function isNonWeekdaySlot(slotType: SlotType): boolean {
  return slotType !== "weekday_night";
}

/** 休日系スロット（平日夜間以外）かどうか */
function isHolidaySlot(slotType: SlotType): boolean {
  return (
    slotType === "sat_day" ||
    slotType === "sat_night" ||
    slotType === "sun_hol_day" ||
    slotType === "sun_hol_night" ||
    slotType === "long_hol_day" ||
    slotType === "long_hol_night"
  );
}

/** 2つの日付文字列（YYYY-MM-DD）間の差分（日数）を返す */
function diffDays(dateStr1: string, dateStr2: string): number {
  const d1 = parseDateStr(dateStr1).getTime();
  const d2 = parseDateStr(dateStr2).getTime();
  return Math.abs(d2 - d1) / (1000 * 60 * 60 * 24);
}

/**
 * ワーカーIDと全カレンダー状態から、そのワーカーのアサイン済み日付を取得する。
 * excludeKey は計算から除外するスロット（現在バリデーション中のスロット自身）。
 */
function getWorkerAssignedDates(
  workerId: string,
  calendarState: CalendarState,
  excludeKey?: { dateStr: string; slotType: SlotType },
): string[] {
  const dates: string[] = [];
  for (const [dateStr, dayState] of Object.entries(calendarState)) {
    for (const [slotType, slotState] of Object.entries(dayState)) {
      if (
        excludeKey &&
        excludeKey.dateStr === dateStr &&
        excludeKey.slotType === slotType
      ) {
        continue;
      }
      if (slotState.workerSelections.includes(workerId)) {
        if (!dates.includes(dateStr)) {
          dates.push(dateStr);
        }
      }
    }
  }
  return dates.sort();
}

/**
 * ルール1: 1人1日1枠制限
 * 同日に複数のスロットへアサインされているワーカーを検出する。
 */
export function validateDailyDuplicate(
  dateStr: string,
  slotType: SlotType,
  workers: readonly (string | null)[],
  calendarState: CalendarState,
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers.filter((id): id is string => id !== null);

  for (const workerId of assignedWorkers) {
    const worker = workerMap.get(workerId);
    if (!worker) continue;

    const dayState = calendarState[dateStr];
    if (!dayState) continue;

    for (const [otherSlotType, otherSlot] of Object.entries(dayState)) {
      if (otherSlotType === slotType) continue;
      if (otherSlot.workerSelections.includes(workerId)) {
        violations.push({
          code: "DAILY_DUPLICATE",
          severity: "error",
          message: `${worker.name} は同日に複数の枠にアサインされています`,
          workerIds: [workerId],
        });
        break;
      }
    }
  }

  return violations;
}

/**
 * ルール2: 所属課の重複禁止
 * 同じスロット内に同じ所属課のワーカーが複数いる場合、エラー。
 */
export function validateSameDepartment(
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  if (assignedWorkers.length < 2) return [];

  const seen = new Set<string>();
  const duplicateDepts = new Set<string>();
  for (const w of assignedWorkers) {
    if (seen.has(w.department_id)) duplicateDepts.add(w.department_id);
    seen.add(w.department_id);
  }

  if (duplicateDepts.size === 0) return [];

  const workerIds = assignedWorkers
    .filter((w) => duplicateDepts.has(w.department_id))
    .map((w) => w.id);

  return [
    {
      code: "SAME_DEPARTMENT",
      severity: "error",
      message: "同じ所属課のメンバーが同一枠にアサインされています",
      workerIds,
    },
  ];
}

/**
 * ルール3: スキルランクAの必須
 * 全員がアサイン済みの場合のみ検証する。
 */
export function validateSkillRankA(
  workers: readonly (string | null)[],
  requiredHeadcount: number,
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  if (assignedWorkers.length < requiredHeadcount) return [];

  const hasRankA = assignedWorkers.some((w) => w.skill_rank === "rank_a");
  if (hasRankA) return [];

  return [
    {
      code: "SKILL_RANK_A",
      severity: "error",
      message: "ランクAのメンバーが含まれていません",
      workerIds: assignedWorkers.map((w) => w.id),
    },
  ];
}

/**
 * ルール4: 中9日以上の勤務間隔
 * 同一ワーカーの他アサインと10日未満の間隔がある場合エラー。
 */
export function validateWorkInterval(
  dateStr: string,
  slotType: SlotType,
  workers: readonly (string | null)[],
  calendarState: CalendarState,
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers.filter((id): id is string => id !== null);

  for (const workerId of assignedWorkers) {
    const worker = workerMap.get(workerId);
    if (!worker) continue;

    const otherDates = getWorkerAssignedDates(workerId, calendarState, {
      dateStr,
      slotType,
    });

    for (const otherDate of otherDates) {
      const diff = diffDays(dateStr, otherDate);
      if (diff < 10) {
        violations.push({
          code: "WORK_INTERVAL",
          severity: "error",
          message: `${worker.name} の勤務間隔が中9日を満たしていません（${Math.round(diff) - 1}日間隔）`,
          workerIds: [workerId],
        });
        break;
      }
    }
  }

  return violations;
}

/**
 * ルール5: 特別雇用者の枠制限
 * 特別雇用者（is_special=true）は平日夜間（weekday_night）以外の枠にはアサイン不可。
 */
export function validateSpecialEmployment(
  slotType: SlotType,
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  if (!isNonWeekdaySlot(slotType)) return [];

  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  for (const worker of assignedWorkers) {
    if (worker.is_special) {
      violations.push({
        code: "SPECIAL_EMPLOYMENT",
        severity: "error",
        message: `${worker.name} は特別雇用者のため、平日夜間以外の枠にはアサインできません`,
        workerIds: [worker.id],
      });
    }
  }

  return violations;
}

/**
 * 任意ルール: 休日の連続回避 (Warning)
 * 同一ワーカーが直前・直後の連続する日にも休日系スロットへアサインされている場合に警告。
 */
export function validateConsecutiveHolidays(
  dateStr: string,
  slotType: SlotType,
  workers: readonly (string | null)[],
  calendarState: CalendarState,
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  if (!isHolidaySlot(slotType)) return [];

  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers.filter((id): id is string => id !== null);
  const oneDayMs = 1000 * 60 * 60 * 24;
  const currentMs = parseDateStr(dateStr).getTime();

  for (const workerId of assignedWorkers) {
    const worker = workerMap.get(workerId);
    if (!worker) continue;

    const otherDates = getWorkerAssignedDates(workerId, calendarState, {
      dateStr,
      slotType,
    });

    for (const otherDate of otherDates) {
      const diff = Math.abs(currentMs - parseDateStr(otherDate).getTime());
      // 隣接していない日（1日超）はスキップし、隣接日（diff <= oneDayMs）のみ処理する
      if (diff > oneDayMs) continue;

      // 隣接日のその割り当てが休日スロットかどうか確認
      const otherDayState = calendarState[otherDate];
      if (!otherDayState) continue;

      const hasAdjacentHolidayAssign = Object.entries(otherDayState).some(
        ([st, s]) =>
          isHolidaySlot(st as SlotType) && s.workerSelections.includes(workerId),
      );

      if (hasAdjacentHolidayAssign) {
        violations.push({
          code: "CONSECUTIVE_HOLIDAYS",
          severity: "warning",
          message: `${worker.name} は連続して休日枠にアサインされています`,
          workerIds: [workerId],
        });
        break;
      }
    }
  }

  return violations;
}

/** 1スロットの全バリデーションを実行して違反リストを返す */
export function validateSlot(
  dateStr: string,
  slotType: SlotType,
  workers: readonly (string | null)[],
  requiredHeadcount: number,
  calendarState: CalendarState,
  workerMap: Map<string, Worker>,
): ValidationViolation[] {
  const assignedCount = workers.filter((id) => id !== null).length;
  if (assignedCount === 0) return [];

  return [
    ...validateDailyDuplicate(dateStr, slotType, workers, calendarState, workerMap),
    ...validateSameDepartment(workers, workerMap),
    ...validateSkillRankA(workers, requiredHeadcount, workerMap),
    ...validateWorkInterval(dateStr, slotType, workers, calendarState, workerMap),
    ...validateSpecialEmployment(slotType, workers, workerMap),
    ...validateConsecutiveHolidays(dateStr, slotType, workers, calendarState, workerMap),
  ];
}
