// frontend/hooks/useAvailableWorkers.ts
// 選択中のスロットの状況に基づいて、アサイン可能なWorkerを算出するカスタムフック
"use client";

import { useMemo } from "react";

import type { CustomRule } from "@/types/customRule";
import type { EmploymentType } from "@/types/employmentType";
import type { CalendarState, SlotType } from "@/types/shiftRequirement";
import type { AnnualShiftLimitsConfig, ShiftRulesConfig } from "@/types/shiftRules";
import type { TenantSkillRank } from "@/types/skillRank";
import type { WorkerStatsResponse } from "@/types/workerStats";
import type { Worker } from "@/types/worker";

/** 平日夜間以外スロットタイプ（sat_day / sat_night 含む全休日系） */
const HOLIDAY_SLOT_TYPES = new Set<SlotType>([
  "sat_day",
  "sat_night",
  "sun_hol_day",
  "sun_hol_night",
  "long_hol_day",
  "long_hol_night",
  "sat_pre_hol_night",
]);

/** 生年月日文字列（YYYY-MM-DD）と基準日から年齢を計算する */
function calcAgeAt(birthDateStr: string, referenceDate: Date): number {
  const [by, bm, bd] = birthDateStr.split("-").map(Number);
  let age = referenceDate.getFullYear() - by;
  const hasBirthdayPassed =
    referenceDate.getMonth() + 1 > bm ||
    (referenceDate.getMonth() + 1 === bm && referenceDate.getDate() >= bd);
  if (!hasBirthdayPassed) age -= 1;
  return Math.max(0, age);
}

export interface AvailableWorkersResult {
  /** フィルタリング後のWorkerリスト */
  availableWorkers: Worker[];
  /** 全Worker数（フィルタ前） */
  totalWorkerCount: number;
  /** フィルタ適用済みかどうか */
  isFiltered: boolean;
  /** 特定のWorkerがアサイン可能かチェックする */
  isWorkerAvailable: (workerId: string) => boolean;
}

interface UseAvailableWorkersOptions {
  /** 全Workerリスト */
  workers: Worker[];
  /** スキルランクの一覧 */
  skillRanks: TenantSkillRank[];
  /** シフトルール設定（未設定の場合はデフォルト制約を適用） */
  rules?: ShiftRulesConfig;
  /** 対象スロットタイプ */
  slotType: SlotType | null;
  /** 対象スロットの現在のアサイン済みWorkerID一覧 */
  assignedWorkerIds: (string | null)[];
  /** 全表示モード（制約無視） */
  showAll: boolean;
  /** ワーカー年間統計（年間上限チェックに使用） */
  workerStats?: WorkerStatsResponse[];
  /** 年間シフト回数上限設定 */
  annualLimits?: AnnualShiftLimitsConfig;
  /** 作成中カレンダーステート（進行中アサインのカウント・間隔チェックに使用） */
  calendarState?: CalendarState;
  /** 選択中スロットの日付（YYYY-MM-DD）。interval チェックと進行中カウント除外に使用 */
  currentDateStr?: string;
  /** シフト最小間隔（日数）。WORK_INTERVAL フィルタリングに使用 */
  minIntervalDays?: number;
  /** 前月の直近シフト日付マップ（workerId → last_shift_date）。月跨ぎ間隔チェックに使用 */
  prevMonthDatesByWorker?: Record<string, string | null>;
  /** 雇用形態マップ（employment_type_id → EmploymentType）。allowed_slot_types フィルタリングに使用 */
  employmentTypeMap?: Map<string, EmploymentType>;
  /** カスタムルールリスト。is_assign_prohibited=true のWorkerを除外するために使用 */
  customRules?: CustomRule[];
}

/**
 * 選択中スロットの状況とルールに基づいてアサイン可能なWorkerリストを算出するフック。
 * rules が未設定の場合もデフォルト制約（リーダー必須・同一課NG・特別雇用除外）を適用する。
 */
export function useAvailableWorkers({
  workers,
  skillRanks,
  rules,
  slotType,
  assignedWorkerIds,
  showAll,
  workerStats,
  annualLimits,
  calendarState,
  currentDateStr,
  minIntervalDays,
  prevMonthDatesByWorker,
  employmentTypeMap,
  customRules,
}: UseAvailableWorkersOptions): AvailableWorkersResult {
  const skillRankMap = useMemo(
    () => new Map(skillRanks.map((r) => [r.id, r])),
    [skillRanks],
  );

  const assignedSet = useMemo(
    () => new Set(assignedWorkerIds.filter((id): id is string => id !== null)),
    [assignedWorkerIds],
  );

  /** ワーカー年間統計マップ */
  const workerStatsMap = useMemo(
    () => workerStats ? new Map(workerStats.map((s) => [s.worker_id, s])) : undefined,
    [workerStats],
  );

  /**
   * 進行中アサインの集計（現在スロットを除く）。
   * workerID → { total: 総アサイン数, counts: スロット種別ごとカウント, dates: アサイン日付セット }
   */
  const inProgressDataByWorker = useMemo(() => {
    const result = new Map<string, { total: number; counts: Record<string, number>; dates: Set<string> }>();
    if (!calendarState) return result;

    for (const [dateStr, dayState] of Object.entries(calendarState)) {
      for (const [st, slotState] of Object.entries(dayState)) {
        // 現在選択中のスロットはスキップ（+1 カウントは後で別途加算）
        if (dateStr === currentDateStr && st === (slotType as string)) continue;

        // long_hol_day / long_hol_night は年間上限集計で sun_hol 系に合算する（仕様通り）
        const countKey =
          st === "long_hol_day" ? "sun_hol_day" :
          st === "long_hol_night" ? "sun_hol_night" : st;

        for (const workerId of slotState.workerSelections) {
          if (!workerId) continue;
          if (!result.has(workerId)) {
            result.set(workerId, { total: 0, counts: {}, dates: new Set() });
          }
          const entry = result.get(workerId)!;
          entry.total += 1;
          entry.counts[countKey] = (entry.counts[countKey] ?? 0) + 1;
          entry.dates.add(dateStr);
        }
      }
    }

    return result;
  }, [calendarState, currentDateStr, slotType]);

  // ルール由来の設定（未設定時はデフォルト値を適用）
  const allowSameDepartment = rules?.allow_same_department ?? false;

  /** カスタムルールマップ（custom_rule_id → CustomRule） */
  const customRuleMap = useMemo(
    () => customRules ? new Map(customRules.map((r) => [r.id, r])) : undefined,
    [customRules],
  );

  const availableWorkers = useMemo(() => {
    if (showAll || slotType === null) return workers;

    return workers.filter((w) => {
      // is_assign_prohibited=true のWorkerを最初に除外
      if (customRuleMap && w.custom_rule_id) {
        const customRule = customRuleMap.get(w.custom_rule_id);
        if (customRule?.is_assign_prohibited) return false;
      }

      // すでにアサイン済みのWorkerは除外
      if (assignedSet.has(w.id)) return false;

      const rank = skillRankMap.get(w.skill_rank_id);

      // 例1: リーダー必須チェック
      // アサイン済みにリーダー適性者がいない場合はリーダー適性者のみ表示
      const hasLeader = [...assignedSet].some((id) => {
        const aw = workers.find((wk) => wk.id === id);
        if (!aw) return false;
        const ar = skillRankMap.get(aw.skill_rank_id);
        return ar?.is_leader_eligible ?? false;
      });

      if (!hasLeader && !(rank?.is_leader_eligible ?? false)) {
        return false;
      }

      // 例2: 同一所属課NGチェック
      if (!allowSameDepartment && assignedSet.size > 0) {
        const assignedDepts = new Set(
          [...assignedSet]
            .map((id) => workers.find((wk) => wk.id === id)?.department_id)
            .filter((d): d is string => !!d),
        );
        if (assignedDepts.has(w.department_id)) return false;
      }

      // 例3: 雇用形態の allowed_slot_types チェック（新ロジック）
      // 雇用形態が非デフォルトで allowed_slot_types が設定されている場合、
      // そのスロット種別以外は除外する。
      if (employmentTypeMap && w.employment_type_id) {
        const et = employmentTypeMap.get(w.employment_type_id);
        if (et && !et.is_default) {
          const globalAllowedSlots = rules?.special_employment_shifts ?? ["weekday_night"];
          const allowedSlots =
            et.rule?.allowed_slot_types && et.rule.allowed_slot_types.length > 0
              ? et.rule.allowed_slot_types
              : globalAllowedSlots;
          if (!(allowedSlots as string[]).includes(slotType)) {
            return false;
          }
        }
      } else if (HOLIDAY_SLOT_TYPES.has(slotType) && w.is_special) {
        // 後方互換: employmentTypeMap がない場合は is_special フラグで判定
        return false;
      }

      // 例4: シフト間隔チェック（WORK_INTERVAL）
      // minIntervalDays === 0 は制限なし（ルール設定でのデフォルト回避値）のためスキップ
      if (currentDateStr && minIntervalDays !== undefined && minIntervalDays > 0) {
        const currentDateMs = new Date(currentDateStr).getTime();
        /** 1日をミリ秒で表した定数 */
        const MS_PER_DAY = 86_400_000;

        // 前月の直近シフト日付チェック（月跨ぎ）
        const prevDate = prevMonthDatesByWorker?.[w.id];
        if (prevDate) {
          const diffDays = Math.abs(currentDateMs - new Date(prevDate).getTime()) / MS_PER_DAY;
          if (diffDays < minIntervalDays) return false;
        }

        // 進行中アサインの日付との間隔チェック
        const inProgress = inProgressDataByWorker.get(w.id);
        if (inProgress) {
          for (const dateStr of inProgress.dates) {
            const diffDays = Math.abs(currentDateMs - new Date(dateStr).getTime()) / MS_PER_DAY;
            if (diffDays < minIntervalDays) return false;
          }
        }
      }

      // 例5: 年間上限超過チェック（showAll=false の場合のみ）
      if (workerStatsMap && annualLimits) {
        const stats = workerStatsMap.get(w.id);
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

        // 進行中アサインのカウントを上乗せ
        const inProgress = inProgressDataByWorker.get(w.id);
        if (inProgress) {
          total += inProgress.total;
          for (const [key, val] of Object.entries(inProgress.counts)) {
            if (key in counts) {
              counts[key] += val;
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

        // 年間合計が上限を超える場合は除外
        if (annualLimits.annual_total > 0 && total > annualLimits.annual_total) {
          return false;
        }

        // 各スロット種別の上限チェック
        const slotLimitMap: Array<[string, number]> = [
          ["weekday_night", annualLimits.weekday_night],
          ["sat_day", annualLimits.sat_day],
          ["sat_night", annualLimits.sat_night],
          ["sun_hol_day", annualLimits.sun_hol_day],
          ["sun_hol_night", annualLimits.sun_hol_night],
          ["sat_pre_hol_night", annualLimits.sat_pre_hol_night],
        ];

        for (const [stKey, limit] of slotLimitMap) {
          if (limit > 0 && (counts[stKey] ?? 0) > limit) {
            return false;
          }
        }
      }

      // 例6: 合計年齢上限フィルタ
      if (rules && currentDateStr) {
        const maxTotalAge = rules.max_total_age ?? 120;
        if (maxTotalAge > 0) {
          const [refYear, refMonth] = currentDateStr.split("-").map(Number);
          const referenceDate = new Date(refYear, refMonth - 1, 1);

          // 既にアサイン済みワーカーの年齢合計を計算
          const assignedAgeSum = [...assignedSet].reduce((sum, id) => {
            const aw = workers.find((wk) => wk.id === id);
            if (!aw || !aw.birth_date) return sum;
            return sum + calcAgeAt(aw.birth_date, referenceDate);
          }, 0);

          // 候補ワーカーの年齢を加算して上限チェック
          const candidateAge = w.birth_date
            ? calcAgeAt(w.birth_date, referenceDate)
            : 0;
          if (assignedAgeSum + candidateAge > maxTotalAge) {
            return false;
          }
        }
      }

      // 例7: 平日夜間以外シフト回数上限フィルタ
      if (rules && calendarState && slotType && HOLIDAY_SLOT_TYPES.has(slotType)) {
        const limit = rules.max_non_weekday_night_per_period ?? 1;
        if (limit > 0) {
          // 進行中アサインの平日夜間以外スロットカウント（現在スロットを除く）
          let nonWeekdayNightCount = 0;
          for (const [calDateStr, dayState] of Object.entries(calendarState)) {
            for (const [calSt, slotState] of Object.entries(dayState)) {
              if (calDateStr === currentDateStr && calSt === (slotType as string)) continue;
              if (!HOLIDAY_SLOT_TYPES.has(calSt as SlotType)) continue;
              if (slotState.workerSelections.includes(w.id)) {
                nonWeekdayNightCount += 1;
              }
            }
          }
          // 今回のアサイン分を含めて上限チェック
          if (nonWeekdayNightCount + 1 > limit) {
            return false;
          }
        }
      }

      return true;
    });
  }, [workers, skillRankMap, assignedSet, allowSameDepartment, slotType, showAll, workerStatsMap, annualLimits, currentDateStr, minIntervalDays, prevMonthDatesByWorker, inProgressDataByWorker, rules, calendarState, employmentTypeMap, customRuleMap]);

  const isWorkerAvailable = useMemo(() => {
    const availableSet = new Set(availableWorkers.map((w) => w.id));
    return (workerId: string) => availableSet.has(workerId);
  }, [availableWorkers]);

  return {
    availableWorkers,
    totalWorkerCount: workers.length,
    isFiltered: !showAll && availableWorkers.length < workers.length,
    isWorkerAvailable,
  };
}
