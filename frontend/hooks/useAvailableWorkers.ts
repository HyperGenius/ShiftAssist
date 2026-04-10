// frontend/hooks/useAvailableWorkers.ts
// 選択中のスロットの状況に基づいて、アサイン可能なWorkerを算出するカスタムフック
"use client";

import { useMemo } from "react";

import type { SlotType } from "@/types/shiftRequirement";
import type { AnnualShiftLimitsConfig, ShiftRulesConfig } from "@/types/shiftRules";
import type { TenantSkillRank } from "@/types/skillRank";
import type { WorkerStatsResponse } from "@/types/workerStats";
import type { Worker } from "@/types/worker";

/** 休日系スロットタイプ */
const HOLIDAY_SLOT_TYPES = new Set<SlotType>([
  "sun_hol_day",
  "sun_hol_night",
  "long_hol_day",
  "long_hol_night",
  "sat_pre_hol_night",
]);

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

  // ルール由来の設定（未設定時はデフォルト値を適用）
  const allowSameDepartment = rules?.allow_same_department ?? false;

  const availableWorkers = useMemo(() => {
    if (showAll || slotType === null) return workers;

    return workers.filter((w) => {
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

      // 例3: 休日スロットの場合、特別雇用者を除外
      if (HOLIDAY_SLOT_TYPES.has(slotType) && w.is_special) {
        return false;
      }

      // 例4: 年間上限超過チェック（showAll=false の場合のみ）
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

      return true;
    });
  }, [workers, skillRankMap, assignedSet, allowSameDepartment, slotType, showAll, workerStatsMap, annualLimits]);

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
