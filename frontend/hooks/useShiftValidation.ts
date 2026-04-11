// frontend/hooks/useShiftValidation.ts
// カレンダー全体のシフトバリデーションを管理するカスタムフック
"use client";

import { useMemo } from "react";

import type { CalendarState, SlotType } from "@/types/shiftRequirement";
import type { AnnualShiftLimitsConfig, ShiftRulesConfig } from "@/types/shiftRules";
import type { TenantSkillRank } from "@/types/skillRank";
import type { ValidationContextWorkerStats } from "@/types/validationContext";
import type { WorkerStatsResponse } from "@/types/workerStats";
import type { Worker } from "@/types/worker";
import { validateSlot, type ValidationViolation } from "@/utils/shiftValidators";

/** スロットキー: `${dateStr}__${slotType}` */
export type SlotKey = string;

/** スロットキーをビルドするヘルパー */
export function buildSlotKey(dateStr: string, slotType: SlotType): SlotKey {
  return `${dateStr}__${slotType}`;
}

/** バリデーション結果マップ: スロットキー → 違反リスト */
export type ValidationMap = Record<SlotKey, ValidationViolation[]>;

/**
 * カレンダー全体のバリデーション結果を返すカスタムフック。
 * calendarState、workers、または rules が変化した際に再計算される。
 *
 * workerStats を渡すと、前月の直近シフト日付も `WORK_INTERVAL` チェックに含まれる。
 * これにより月跨ぎ（例: 3月31日→4月1日）のアサイン間隔違反を検出できる。
 *
 * annualWorkerStats と annualLimits を渡すと、年間シフト回数上限チェックも実行される。
 */
export function useShiftValidation(
  calendarState: CalendarState,
  workers: Worker[],
  rules?: ShiftRulesConfig,
  skillRanks?: TenantSkillRank[],
  workerStats?: ValidationContextWorkerStats[],
  annualWorkerStats?: WorkerStatsResponse[],
  annualLimits?: AnnualShiftLimitsConfig,
): ValidationMap {
  const workerMap = useMemo(
    () => new Map(workers.map((w) => [w.id, w])),
    [workers],
  );

  const skillRankMap = useMemo(
    () => new Map((skillRanks ?? []).map((r) => [r.id, r])),
    [skillRanks],
  );

  /**
   * 前月の直近シフト日付マップ（workerId → last_shift_date）。
   * バリデーションコンテキストから取得した confirmed（published）プランのデータを使う。
   */
  const prevMonthDatesByWorker = useMemo<Record<string, string | null>>(() => {
    if (!workerStats || workerStats.length === 0) return {};
    return Object.fromEntries(
      workerStats.map((s) => [s.worker_id, s.last_shift_date]),
    );
  }, [workerStats]);

  /** 年間統計マップ（workerId → WorkerStatsResponse）。 */
  const workerStatsMap = useMemo(() => {
    if (!annualWorkerStats) return undefined;
    return new Map(annualWorkerStats.map((s) => [s.worker_id, s]));
  }, [annualWorkerStats]);

  const validationMap = useMemo(() => {
    const result: ValidationMap = {};

    for (const [dateStr, dayState] of Object.entries(calendarState)) {
      for (const [slotType, slotState] of Object.entries(dayState)) {
        const violations = validateSlot(
          dateStr,
          slotType as SlotType,
          slotState.workerSelections,
          slotState.required_headcount,
          calendarState,
          workerMap,
          rules,
          skillRankMap,
          prevMonthDatesByWorker,
          workerStatsMap,
          annualLimits,
        );
        if (violations.length > 0) {
          result[buildSlotKey(dateStr, slotType as SlotType)] = violations;
        }
      }
    }

    return result;
  }, [calendarState, workerMap, rules, skillRankMap, prevMonthDatesByWorker, workerStatsMap, annualLimits]);

  return validationMap;
}
