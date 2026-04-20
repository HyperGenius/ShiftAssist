// frontend/utils/shiftValidators.ts
// シフトバリデーションのための純粋関数群

import type { EmploymentType } from "@/types/employmentType";
import type { CalendarState, SlotType } from "@/types/shiftRequirement";
import type { AnnualShiftLimitsConfig, ShiftRulesConfig } from "@/types/shiftRules";
import type { TenantSkillRank } from "@/types/skillRank";
import type { WorkerStatsResponse } from "@/types/workerStats";
import type { Worker } from "@/types/worker";
import { parseDateStr } from "@/utils/calendarUtils";

export type ValidationCode =
  | "DAILY_DUPLICATE" // 1人1日1枠: 同日の複数枠への重複アサイン
  | "SAME_DEPARTMENT" // 同じ所属課同士のペア
  | "SKILL_RANK_A" // スキルランクAがペアに含まれない
  | "WORK_INTERVAL" // 中9日未満の勤務間隔
  | "ASSIGN_PROHIBITED" // アサイン不可ルールによるアサイン禁止
  | "SPECIAL_EMPLOYMENT" // 特別雇用者の枠制限違反
  | "NEW_HIRE_TENURE" // 採用後の期間制限
  | "TRANSFER_TENURE" // 事業本部間転入後の期間制限
  | "TOTAL_AGE_LIMIT" // スロット内ワーカーの合計年齢上限超過
  | "NON_WEEKDAY_NIGHT_LIMIT" // 平日夜間以外シフト回数上限超過
  | "CONSECUTIVE_HOLIDAYS" // 休日の連続アサイン (Warning)
  | "ANNUAL_TOTAL_SHIFTS" // 年間総シフト回数上限 (Warning)
  | "ANNUAL_WEEKDAY_NIGHT" // 年間平日夜間上限 (Warning)
  | "ANNUAL_SAT_DAY" // 年間土曜昼間上限 (Warning)
  | "ANNUAL_SAT_NIGHT" // 年間土曜夜間上限 (Warning)
  | "ANNUAL_SUN_HOL_DAY" // 年間日祝昼間上限 (Warning)
  | "ANNUAL_SUN_HOL_NIGHT" // 年間日祝夜間上限 (Warning)
  | "ANNUAL_SAT_PRE_HOL_NIGHT"; // 年間土曜・祝前日夜間上限 (Warning)

export type ValidationSeverity = "error" | "warning";

export interface ValidationViolation {
  code: ValidationCode;
  severity: ValidationSeverity;
  message: string;
  workerIds: string[];
}

/** 休日系スロット（平日夜間以外）かどうか */
function isHolidaySlot(slotType: SlotType): boolean {
  return (
    slotType === "sat_day" ||
    slotType === "sat_night" ||
    slotType === "sun_hol_day" ||
    slotType === "sun_hol_night" ||
    slotType === "long_hol_day" ||
    slotType === "long_hol_night" ||
    slotType === "sat_pre_hol_night"
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
  rules?: Pick<ShiftRulesConfig, "allow_same_department">,
): ValidationViolation[] {
  if (rules?.allow_same_department) return [];

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
 * ルール3: リーダー適性（is_leader_eligible）の必須チェック
 * 全員がアサイン済みの場合のみ検証する。
 * skillRankMap が空の場合はチェックをスキップする。
 */
export function validateSkillRankA(
  workers: readonly (string | null)[],
  requiredHeadcount: number,
  workerMap: Map<string, Worker>,
  rules?: Pick<ShiftRulesConfig, "require_skill_ranks">,
  skillRankMap?: Map<string, TenantSkillRank>,
): ValidationViolation[] {
  const requiredRanks = rules?.require_skill_ranks ?? ["rank_a"];
  if (!requiredRanks.length) return [];

  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  if (assignedWorkers.length < requiredHeadcount) return [];

  // skillRankMap が提供されている場合は is_leader_eligible でチェック
  if (skillRankMap && skillRankMap.size > 0) {
    const hasLeaderEligible = assignedWorkers.some((w) => {
      const rank = skillRankMap.get(w.skill_rank_id);
      return rank?.is_leader_eligible === true;
    });
    if (hasLeaderEligible) return [];
  } else {
    // skillRankMap が未提供の場合はチェックをスキップ
    return [];
  }

  return [
    {
      code: "SKILL_RANK_A",
      severity: "error",
      message: "リーダー適性（is_leader_eligible）を持つメンバーが含まれていません",
      workerIds: assignedWorkers.map((w) => w.id),
    },
  ];
}

/**
 * ルール4: 中9日以上の勤務間隔
 * 同一ワーカーの他アサインとmin_interval_days日未満の間隔がある場合エラー。
 * prevMonthDatesByWorker に前月の直近シフト日付（published プランから取得）を
 * 渡すことで月跨ぎのバリデーションにも対応する。
 */
export function validateWorkInterval(
  dateStr: string,
  slotType: SlotType,
  workers: readonly (string | null)[],
  calendarState: CalendarState,
  workerMap: Map<string, Worker>,
  rules?: Pick<ShiftRulesConfig, "min_interval_days">,
  prevMonthDatesByWorker?: Record<string, string | null>,
): ValidationViolation[] {
  const minIntervalDays = rules?.min_interval_days ?? 10;
  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers.filter((id): id is string => id !== null);

  for (const workerId of assignedWorkers) {
    const worker = workerMap.get(workerId);
    if (!worker) continue;

    // 当月カレンダー内での間隔チェック
    const otherDates = getWorkerAssignedDates(workerId, calendarState, {
      dateStr,
      slotType,
    });

    let violated = false;
    for (const otherDate of otherDates) {
      const diff = diffDays(dateStr, otherDate);
      if (diff < minIntervalDays) {
        violations.push({
          code: "WORK_INTERVAL",
          severity: "error",
          message: `${worker.name} の勤務間隔が中${minIntervalDays - 1}日を満たしていません（${Math.round(diff) - 1}日間隔）`,
          workerIds: [workerId],
        });
        violated = true;
        break;
      }
    }

    if (violated) continue;

    // 前月の直近シフト日付との月跨ぎ間隔チェック
    const prevDate = prevMonthDatesByWorker?.[workerId];
    if (prevDate) {
      const diff = diffDays(dateStr, prevDate);
      if (diff > 0 && diff < minIntervalDays) {
        violations.push({
          code: "WORK_INTERVAL",
          severity: "error",
          message: `${worker.name} の勤務間隔が中${minIntervalDays - 1}日を満たしていません（${Math.round(diff) - 1}日間隔）`,
          workerIds: [workerId],
        });
      }
    }
  }

  return violations;
}

/**
 * カスタムルール: アサイン不可チェック（ASSIGN_PROHIBITED）
 * is_assign_prohibited=true のカスタムルールが設定されているWorkerは
 * allowed_slot_types の設定に関わらず全スロットへのアサインを禁止する。
 */
export function validateAssignProhibited(
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
  customRuleMap?: Map<string, { is_assign_prohibited?: boolean; allowed_slot_types: string[] | null }>,
): ValidationViolation[] {
  if (!customRuleMap) return [];

  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  for (const worker of assignedWorkers) {
    if (!worker.custom_rule_id) continue;
    const customRule = customRuleMap.get(worker.custom_rule_id);
    if (customRule?.is_assign_prohibited) {
      violations.push({
        code: "ASSIGN_PROHIBITED",
        severity: "error",
        message: `${worker.name} はアサイン不可ルールにより、いずれの枠にもアサインできません`,
        workerIds: [worker.id],
      });
    }
  }

  return violations;
}

/**
 * ルール5: 特別雇用者の枠制限
 * 非デフォルト雇用形態に紐付くWorker（または is_special=true のWorker）は
 * 許可された枠以外にはアサイン不可。
 * 優先順位: カスタムルール > 雇用形態別ルール > グローバルルール。
 * カスタムルールの allowed_slot_types が設定されているWorkerは雇用形態にかかわらず制限される。
 */
export function validateSpecialEmployment(
  slotType: SlotType,
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
  rules?: Pick<ShiftRulesConfig, "special_employment_shifts">,
  employmentTypeMap?: Map<string, EmploymentType>,
  customRuleMap?: Map<string, { is_assign_prohibited?: boolean; allowed_slot_types: string[] | null }>,
): ValidationViolation[] {
  const globalAllowedSlots = rules?.special_employment_shifts ?? ["weekday_night"];

  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  for (const worker of assignedWorkers) {
    // is_assign_prohibited=true の Worker は validateAssignProhibited の責務に委ねる
    if (customRuleMap && worker.custom_rule_id) {
      const customRule = customRuleMap.get(worker.custom_rule_id);
      if (customRule?.is_assign_prohibited) {
        continue;
      }
    }

    // カスタムルールが設定されており allowed_slot_types が指定されている場合は最優先
    if (customRuleMap && worker.custom_rule_id) {
      const customRule = customRuleMap.get(worker.custom_rule_id);
      if (customRule && customRule.allowed_slot_types && customRule.allowed_slot_types.length > 0) {
        const allowedSlots = customRule.allowed_slot_types;
        if (!(allowedSlots as string[]).includes(slotType)) {
          const allowedStr = allowedSlots.join("、");
          violations.push({
            code: "SPECIAL_EMPLOYMENT",
            severity: "error",
            message: `${worker.name} のカスタムルールにより、許可された枠（${allowedStr}）以外にはアサインできません`,
            workerIds: [worker.id],
          });
        }
        continue;
      }
    }

    // 雇用形態別ルールチェック（カスタムルールがない場合）
    if (employmentTypeMap && worker.employment_type_id) {
      const et = employmentTypeMap.get(worker.employment_type_id);
      if (et && !et.is_default) {
        // null の場合はグローバル設定にフォールバック。空配列は全スロット禁止として扱う。
        const allowedSlots =
          et.rule?.allowed_slot_types != null
            ? et.rule.allowed_slot_types
            : globalAllowedSlots;
        if (!(allowedSlots as string[]).includes(slotType)) {
          const allowedStr = allowedSlots.join("、");
          violations.push({
            code: "SPECIAL_EMPLOYMENT",
            severity: "error",
            message: `${worker.name} の雇用形態では、許可された枠（${allowedStr}）以外にはアサインできません`,
            workerIds: [worker.id],
          });
        }
        continue;
      }
    }

    // 後方互換: is_special フラグによる旧ロジック
    if (worker.is_special) {
      if (!(globalAllowedSlots as string[]).includes(slotType)) {
        violations.push({
          code: "SPECIAL_EMPLOYMENT",
          severity: "error",
          message: `${worker.name} は特別雇用者のため、平日夜間以外の枠にはアサインできません`,
          workerIds: [worker.id],
        });
      }
    }
  }

  return violations;
}

/**
 * ルール8: 着任・異動後の期間制限
 * - 採用（transfer_type=hired）: joined_at から hired_tenure_months ヶ月未満はアサイン不可。
 * - 事業本部間転入（transfer_type=transfer_in かつ is_cross_division_transfer=true）:
 *   transferred_at（なければ joined_at）から cross_division_transfer_tenure_months ヶ月未満はアサイン不可。
 * 閾値が 0 の場合は制限なし。
 */
export function validateTenureRestriction(
  dateStr: string,
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
  rules?: Pick<
    ShiftRulesConfig,
    "hired_tenure_months" | "cross_division_transfer_tenure_months"
  >,
): ValidationViolation[] {
  const hiredMonths = rules?.hired_tenure_months ?? 6;
  const transferMonths = rules?.cross_division_transfer_tenure_months ?? 3;
  const shiftDate = parseDateStr(dateStr);

  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  for (const worker of assignedWorkers) {
    // 採用（hired）: joined_at から hiredMonths ヶ月チェック
    if (worker.transfer_type === "hired") {
      if (hiredMonths > 0 && worker.joined_at) {
        const months = monthsBetween(parseDateStr(worker.joined_at), shiftDate);
        if (months < hiredMonths) {
          violations.push({
            code: "NEW_HIRE_TENURE",
            severity: "error",
            message: `${worker.name} は採用後${hiredMonths}ヶ月経過していません（着任日: ${worker.joined_at}、あと ${hiredMonths - months} ヶ月必要）`,
            workerIds: [worker.id],
          });
        }
      }
      continue;
    }

    // 事業本部間転入（transfer_in + is_cross_division_transfer）
    if (
      worker.transfer_type === "transfer_in" &&
      worker.is_cross_division_transfer
    ) {
      if (transferMonths > 0) {
        const baseDate = worker.transferred_at ?? worker.joined_at;
        if (baseDate) {
          const months = monthsBetween(parseDateStr(baseDate), shiftDate);
          if (months < transferMonths) {
            violations.push({
              code: "TRANSFER_TENURE",
              severity: "error",
              message: `${worker.name} は事業本部間異動後${transferMonths}ヶ月経過していません（異動日: ${baseDate}、あと ${transferMonths - months} ヶ月必要）`,
              workerIds: [worker.id],
            });
          }
        }
      }
    }
  }

  return violations;
}

/** 2つの Date 間の完全な月数を計算する（切り捨て） */
function monthsBetween(start: Date, end: Date): number {
  let months =
    (end.getFullYear() - start.getFullYear()) * 12 +
    (end.getMonth() - start.getMonth());
  if (end.getDate() < start.getDate()) {
    months -= 1;
  }
  return Math.max(0, months);
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

/**
 * 任意ルール: 年間シフト回数上限チェック (Warning)
 * WorkerStatsResponse を参照して年間合計・各スロット種別の上限を超えているか検証する。
 * - long_hol_day / long_hol_night は sun_hol_day / sun_hol_night に合算する
 * - limits の各フィールドが 0 の場合は制限なし
 * 適用優先順位: カスタムルール > 雇用形態別ルール > グローバルルール（limits）
 */
export function validateAnnualShiftLimits(
  slotType: SlotType,
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
  workerStatsMap: Map<string, WorkerStatsResponse>,
  limits: AnnualShiftLimitsConfig,
  employmentTypeMap?: Map<string, EmploymentType>,
  customRuleMap?: Map<string, { annual_limit_overrides: Record<string, number | null> | null }>,
): ValidationViolation[] {
  const violations: ValidationViolation[] = [];
  const assignedWorkers = workers.filter((id): id is string => id !== null);

  for (const workerId of assignedWorkers) {
    const worker = workerMap.get(workerId);
    if (!worker) continue;

    const stats = workerStatsMap.get(workerId);

    // 実績の集計（long_hol は sun_hol に合算）
    const counts: Record<string, number> = {
      weekday_night: 0,
      sat_day: 0,
      sat_night: 0,
      sun_hol_day: 0,
      sun_hol_night: 0,
      sat_pre_hol_night: 0,
    };
    let total = 0;

    if (stats) {
      for (const s of stats.slot_stats) {
        const st = s.slot_type as string;
        total += s.count;
        if (st === "long_hol_day") {
          counts["sun_hol_day"] += s.count;
        } else if (st === "long_hol_night") {
          counts["sun_hol_night"] += s.count;
        } else if (st in counts) {
          counts[st] += s.count;
        }
      }
    }

    // 今回アサインされるスロット種別を加算
    const currentSt = slotType as string;
    total += 1;
    if (currentSt === "long_hol_day") {
      counts["sun_hol_day"] += 1;
    } else if (currentSt === "long_hol_night") {
      counts["sun_hol_night"] += 1;
    } else if (currentSt in counts) {
      counts[currentSt] += 1;
    }

    // 有効な上限を決定（優先順位: カスタムルール > 雇用形態別 > グローバル）
    let effectiveLimits = limits;

    const customRule = customRuleMap && worker.custom_rule_id
      ? customRuleMap.get(worker.custom_rule_id)
      : null;

    if (customRule?.annual_limit_overrides) {
      const overrides = customRule.annual_limit_overrides;
      effectiveLimits = {
        annual_total: overrides.annual_total ?? limits.annual_total,
        weekday_night: overrides.weekday_night ?? limits.weekday_night,
        sat_day: overrides.sat_day ?? limits.sat_day,
        sat_night: overrides.sat_night ?? limits.sat_night,
        sun_hol_day: overrides.sun_hol_day ?? limits.sun_hol_day,
        sun_hol_night: overrides.sun_hol_night ?? limits.sun_hol_night,
        sat_pre_hol_night: overrides.sat_pre_hol_night ?? limits.sat_pre_hol_night,
      };
    } else if (employmentTypeMap && worker.employment_type_id) {
      const et = employmentTypeMap.get(worker.employment_type_id);
      if (et?.rule?.annual_limit_overrides) {
        const overrides = et.rule.annual_limit_overrides;
        effectiveLimits = {
          annual_total: overrides.annual_total ?? limits.annual_total,
          weekday_night: overrides.weekday_night ?? limits.weekday_night,
          sat_day: overrides.sat_day ?? limits.sat_day,
          sat_night: overrides.sat_night ?? limits.sat_night,
          sun_hol_day: overrides.sun_hol_day ?? limits.sun_hol_day,
          sun_hol_night: overrides.sun_hol_night ?? limits.sun_hol_night,
          sat_pre_hol_night: overrides.sat_pre_hol_night ?? limits.sat_pre_hol_night,
        };
      }
    }

    // 年間合計チェック
    if (effectiveLimits.annual_total > 0 && total > effectiveLimits.annual_total) {
      violations.push({
        code: "ANNUAL_TOTAL_SHIFTS",
        severity: "warning",
        message: `${worker.name} の年間シフト回数が上限（${effectiveLimits.annual_total}回）を超えています（現在: ${total}回）`,
        workerIds: [workerId],
      });
    }

    // 各スロット種別チェック
    const slotLimitMap: Array<[string, ValidationCode, number, string]> = [
      ["weekday_night", "ANNUAL_WEEKDAY_NIGHT", effectiveLimits.weekday_night, "平日夜間"],
      ["sat_day", "ANNUAL_SAT_DAY", effectiveLimits.sat_day, "土曜昼間"],
      ["sat_night", "ANNUAL_SAT_NIGHT", effectiveLimits.sat_night, "土曜夜間"],
      ["sun_hol_day", "ANNUAL_SUN_HOL_DAY", effectiveLimits.sun_hol_day, "日祝昼間"],
      ["sun_hol_night", "ANNUAL_SUN_HOL_NIGHT", effectiveLimits.sun_hol_night, "日祝夜間"],
      ["sat_pre_hol_night", "ANNUAL_SAT_PRE_HOL_NIGHT", effectiveLimits.sat_pre_hol_night, "土曜・祝前日夜間"],
    ];

    for (const [stKey, code, limit, label] of slotLimitMap) {
      if (limit > 0 && (counts[stKey] ?? 0) > limit) {
        violations.push({
          code,
          severity: "warning",
          message: `${worker.name} の${label}年間シフト回数が上限（${limit}回）を超えています（現在: ${counts[stKey]}回）`,
          workerIds: [workerId],
        });
      }
    }
  }

  return violations;
}

/**
 * シフト日文字列（YYYY-MM-DD）から、その月の初日を表す Date を返す。
 */
function firstDayOfMonth(dateStr: string): Date {
  const d = parseDateStr(dateStr);
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

/**
 * 生年月日文字列（YYYY-MM-DD）と基準日から年齢を計算する。
 */
function calculateAgeAt(birthDateStr: string, referenceDate: Date): number {
  const birth = parseDateStr(birthDateStr);
  let age =
    referenceDate.getFullYear() - birth.getFullYear();
  const hasBirthdayPassed =
    referenceDate.getMonth() > birth.getMonth() ||
    (referenceDate.getMonth() === birth.getMonth() &&
      referenceDate.getDate() >= birth.getDate());
  if (!hasBirthdayPassed) age -= 1;
  return Math.max(0, age);
}

/**
 * ルール: 合計年齢上限チェック（TOTAL_AGE_LIMIT）
 * スロット内のワーカーの年齢合計が max_total_age を超えた場合にエラー。
 * max_total_age が 0 の場合は制限なし。
 * birth_date が null のワーカーは計算から除外（0歳扱い）。
 */
export function validateTotalAgeLimit(
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
  rules: Pick<ShiftRulesConfig, "max_total_age">,
  shiftDateStr: string,
): ValidationViolation[] {
  const maxTotalAge = rules.max_total_age ?? 120;
  if (maxTotalAge === 0) return [];

  const assignedWorkers = workers
    .filter((id): id is string => id !== null)
    .map((id) => workerMap.get(id))
    .filter((w): w is Worker => w !== undefined);

  if (assignedWorkers.length === 0) return [];

  const referenceDate = firstDayOfMonth(shiftDateStr);
  const workersWithBirthDate = assignedWorkers.filter(
    (w) => w.birth_date != null,
  );
  const ageSum = workersWithBirthDate.reduce(
    (sum, w) => sum + calculateAgeAt(w.birth_date!, referenceDate),
    0,
  );

  if (ageSum <= maxTotalAge) return [];

  return [
    {
      code: "TOTAL_AGE_LIMIT",
      severity: "error",
      message: `スロット内ワーカーの年齢合計が上限（${maxTotalAge}歳）を超えています（合計: ${ageSum}歳）`,
      workerIds: workersWithBirthDate.map((w) => w.id),
    },
  ];
}

/** 平日夜間以外スロット種別セット */
const NON_WEEKDAY_NIGHT_SLOT_TYPES = new Set<SlotType>([
  "sat_day",
  "sat_night",
  "sun_hol_day",
  "sun_hol_night",
  "long_hol_day",
  "long_hol_night",
  "sat_pre_hol_night",
]);

/**
 * ルール: 平日夜間以外シフト回数上限チェック（NON_WEEKDAY_NIGHT_LIMIT）
 * 対象スロットが平日夜間以外のとき、calendarState 内で同一ワーカーが
 * max_non_weekday_night_per_period 回以上の平日夜間以外スロットにアサインされていれば
 * エラーを返す。max_non_weekday_night_per_period が 0 の場合は制限なし。
 * 対象スロットが weekday_night の場合はルールを適用しない。
 */
export function validateNonWeekdayNightLimit(
  dateStr: string,
  slotType: SlotType,
  workers: readonly (string | null)[],
  calendarState: CalendarState,
  workerMap: Map<string, Worker>,
  rules: Pick<ShiftRulesConfig, "max_non_weekday_night_per_period">,
): ValidationViolation[] {
  const limit = rules.max_non_weekday_night_per_period ?? 1;
  if (limit === 0) return [];
  if (!NON_WEEKDAY_NIGHT_SLOT_TYPES.has(slotType)) return [];

  const assignedWorkers = workers.filter((id): id is string => id !== null);
  const violations: ValidationViolation[] = [];

  for (const workerId of assignedWorkers) {
    const worker = workerMap.get(workerId);
    if (!worker) continue;

    // 現在スロットを除く、カレンダー内の平日夜間以外スロットへのアサイン数をカウント
    let count = 0;
    for (const [calDateStr, dayState] of Object.entries(calendarState)) {
      for (const [calSlotType, slotState] of Object.entries(dayState)) {
        if (calDateStr === dateStr && calSlotType === slotType) continue;
        if (!NON_WEEKDAY_NIGHT_SLOT_TYPES.has(calSlotType as SlotType)) continue;
        if (slotState.workerSelections.includes(workerId)) {
          count += 1;
        }
      }
    }

    // 今回のアサイン分を加算して上限チェック
    if (count + 1 > limit) {
      violations.push({
        code: "NON_WEEKDAY_NIGHT_LIMIT",
        severity: "error",
        message: `${worker.name} は今月の平日夜間以外シフト回数が上限（${limit}回）を超えています（現在: ${count + 1}回）`,
        workerIds: [workerId],
      });
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
  rules?: ShiftRulesConfig,
  skillRankMap?: Map<string, TenantSkillRank>,
  prevMonthDatesByWorker?: Record<string, string | null>,
  workerStatsMap?: Map<string, WorkerStatsResponse>,
  annualLimits?: AnnualShiftLimitsConfig,
  employmentTypeMap?: Map<string, EmploymentType>,
  customRuleMap?: Map<string, { is_assign_prohibited?: boolean; allowed_slot_types: string[] | null; annual_limit_overrides: Record<string, number | null> | null }>,
): ValidationViolation[] {
  const assignedCount = workers.filter((id) => id !== null).length;
  if (assignedCount === 0) return [];

  return [
    ...validateDailyDuplicate(dateStr, slotType, workers, calendarState, workerMap),
    ...validateSameDepartment(workers, workerMap, rules),
    ...validateSkillRankA(workers, requiredHeadcount, workerMap, rules, skillRankMap),
    ...validateWorkInterval(dateStr, slotType, workers, calendarState, workerMap, rules, prevMonthDatesByWorker),
    ...validateAssignProhibited(workers, workerMap, customRuleMap),
    ...validateSpecialEmployment(slotType, workers, workerMap, rules, employmentTypeMap, customRuleMap),
    ...validateTenureRestriction(dateStr, workers, workerMap, rules),
    ...validateConsecutiveHolidays(dateStr, slotType, workers, calendarState, workerMap),
    ...(workerStatsMap && annualLimits
      ? validateAnnualShiftLimits(slotType, workers, workerMap, workerStatsMap, annualLimits, employmentTypeMap, customRuleMap)
      : []),
    ...(rules ? validateTotalAgeLimit(workers, workerMap, rules, dateStr) : []),
    ...(rules
      ? validateNonWeekdayNightLimit(dateStr, slotType, workers, calendarState, workerMap, rules)
      : []),
  ];
}
