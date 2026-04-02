// frontend/hooks/useShiftValidation.ts
// カレンダー全体のシフトバリデーションを管理するカスタムフック
"use client";

import { useMemo } from "react";

import type { CalendarState, SlotType } from "@/types/shiftRequirement";
import type { ShiftRulesConfig } from "@/types/shiftRules";
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
 */
export function useShiftValidation(
  calendarState: CalendarState,
  workers: Worker[],
  rules?: ShiftRulesConfig,
): ValidationMap {
  const workerMap = useMemo(
    () => new Map(workers.map((w) => [w.id, w])),
    [workers],
  );

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
        );
        if (violations.length > 0) {
          result[buildSlotKey(dateStr, slotType as SlotType)] = violations;
        }
      }
    }

    return result;
  }, [calendarState, workerMap, rules]);

  return validationMap;
}
