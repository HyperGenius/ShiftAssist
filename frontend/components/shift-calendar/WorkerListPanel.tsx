"use client";

import { useMemo } from "react";
import Link from "next/link";

import type { Department } from "@/types/department";
import type { EmploymentType } from "@/types/employmentType";
import type { SlotType } from "@/types/shiftRequirement";
import type { ShiftRulesConfig } from "@/types/shiftRules";
import type { TenantSkillRank } from "@/types/skillRank";
import type { Worker } from "@/types/worker";
import type { AggregateStatsResponse } from "@/types/workerStats";
import { useAvailableWorkers } from "@/hooks/useAvailableWorkers";
import { WorkerCard } from "./WorkerCard";
import { SmartSuggestRow, SMART_SUGGEST_GRID_COLS } from "./SmartSuggestRow";

interface WorkerListPanelProps {
  workers: Worker[];
  departments: Department[];
  skillRanks: TenantSkillRank[];
  employmentTypes?: EmploymentType[];
  rules?: ShiftRulesConfig;
  /** 現在アクティブなスロットの種類（フィルタリングに使用） */
  activeSlotType: SlotType | null;
  /** 現在アクティブなスロットのアサイン済みWorkerID */
  activeAssignedWorkerIds: (string | null)[];
  /** 全表示モード（制約無視） */
  showAll: boolean;
  /** 全表示モード変更コールバック */
  onShowAllChange: (value: boolean) => void;
  /** 直近12ヶ月の集計データ（スマートソートと集計情報表示に使用） */
  aggregateStats?: AggregateStatsResponse | null;
  /** 集計データ読み込み中フラグ */
  isAggregateStatsLoading?: boolean;
}

/**
 * シフトアサイン画面の右サイドパネルコンポーネント。
 * Workerの一覧をフィルタリングして表示し、各行はドラッグ可能。
 * 集計データが利用可能な場合は6カラムGridのスマートサジェスト表示とソートを適用する。
 */
export function WorkerListPanel({
  workers,
  departments,
  skillRanks,
  employmentTypes = [],
  rules,
  activeSlotType,
  activeAssignedWorkerIds,
  showAll,
  onShowAllChange,
  aggregateStats,
  isAggregateStatsLoading = false,
}: WorkerListPanelProps) {
  const { availableWorkers, totalWorkerCount, isFiltered } =
    useAvailableWorkers({
      workers,
      skillRanks,
      rules,
      slotType: activeSlotType,
      assignedWorkerIds: activeAssignedWorkerIds,
      showAll,
    });

  // 全Workerのうちフィルタで除外されているIDセット（全表示時はdisabledにしない）
  const availableIds = new Set(availableWorkers.map((w) => w.id));

  // worker_id → AggregateWorkerStats マップ
  const aggregateStatsMap = useMemo(
    () =>
      new Map(
        (aggregateStats?.items ?? []).map((item) => [item.worker_id, item]),
      ),
    [aggregateStats],
  );

  // 雇用形態IDから名称へのマップ
  const employmentTypeNameById = useMemo(
    () => new Map(employmentTypes.map((et) => [et.id, et.name])),
    [employmentTypes],
  );

  // 集計データが存在しない場合に警告を表示するか
  const showNoAggregateWarning =
    !isAggregateStatsLoading &&
    (!aggregateStats || aggregateStats.items.length === 0);

  // 選択中スロットに既にリーダーがいるかチェック
  const slotHasLeader = useMemo(() => {
    const assignedSet = new Set(
      activeAssignedWorkerIds.filter((id): id is string => id !== null),
    );
    const skillRankMap = new Map(skillRanks.map((r) => [r.id, r]));
    return [...assignedSet].some((id) => {
      const aw = workers.find((wk) => wk.id === id);
      if (!aw) return false;
      return skillRankMap.get(aw.skill_rank_id)?.is_leader_eligible ?? false;
    });
  }, [activeAssignedWorkerIds, workers, skillRanks]);

  // スマートソート済みの利用可能Workerリスト
  const sortedAvailableWorkers = useMemo(() => {
    if (showAll) return workers;

    const skillRankMap = new Map(skillRanks.map((r) => [r.id, r]));

    return [...availableWorkers].sort((a, b) => {
      // 1. リーダー優先度: スロットに既にリーダーがいる場合、リーダー適性者を最下位に
      const aIsLeader =
        skillRankMap.get(a.skill_rank_id)?.is_leader_eligible ?? false;
      const bIsLeader =
        skillRankMap.get(b.skill_rank_id)?.is_leader_eligible ?? false;
      if (slotHasLeader && aIsLeader !== bIsLeader) {
        return aIsLeader ? 1 : -1;
      }

      // 2. 勤務平準化: 対象スロットの月平均が少ない順
      if (activeSlotType) {
        const aStats = aggregateStatsMap.get(a.id);
        const bStats = aggregateStatsMap.get(b.id);
        const aAvg =
          aStats?.slot_stats.find((s) => s.slot_type === activeSlotType)
            ?.monthly_avg ?? 0;
        const bAvg =
          bStats?.slot_stats.find((s) => s.slot_type === activeSlotType)
            ?.monthly_avg ?? 0;
        if (aAvg !== bAvg) return aAvg - bAvg;
      }

      // 3. フォールバック: 所属課順 → 氏名順
      const aDept =
        departments.find((d) => d.id === a.department_id)?.name ?? "";
      const bDept =
        departments.find((d) => d.id === b.department_id)?.name ?? "";
      if (aDept !== bDept) return aDept.localeCompare(bDept, "ja");
      return a.name.localeCompare(b.name, "ja");
    });
  }, [
    showAll,
    availableWorkers,
    workers,
    skillRanks,
    slotHasLeader,
    activeSlotType,
    aggregateStatsMap,
    departments,
  ]);

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* パネルヘッダー */}
      <div className="px-3 py-2 border-b border-gray-200">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            対応者リスト
          </h3>
          <span className="text-[10px] text-gray-400">
            {showAll ? `${workers.length}/${totalWorkerCount}` : `${availableWorkers.length}/${totalWorkerCount}`}
          </span>
        </div>

        {/* フィルタ状態表示 */}
        {activeSlotType && isFiltered && !showAll && (
          <p className="text-[10px] text-gray-400 mb-1">
            スマートサジェスト適用中
          </p>
        )}

        {/* 全表示チェックボックス */}
        <label className="flex items-center gap-1.5 cursor-pointer group">
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => onShowAllChange(e.target.checked)}
            className="w-3 h-3 accent-blue-500 cursor-pointer"
          />
          <span className="text-[11px] text-gray-500 group-hover:text-gray-700 transition-colors">
            全表示（制約無視）
          </span>
        </label>
      </div>

      {/* 集計データ未計算時の警告 */}
      {showNoAggregateWarning && (
        <div className="px-2 py-1.5 bg-amber-50 border-b border-amber-200 text-[10px] text-amber-800">
          ⚠️ 集計データが最新ではありません。{" "}
          <Link
            href="/admin/aggregate-stats"
            className="underline hover:text-amber-900"
          >
            シフト集計ページ
          </Link>
          で再計算してください
        </div>
      )}

      {/* グリッドヘッダー */}
      {!showAll && activeSlotType && workers.length > 0 && (
        <div className={`grid items-center gap-x-1 px-1.5 py-0.5 bg-gray-50 border-b border-gray-100 text-[9px] text-gray-400 ${SMART_SUGGEST_GRID_COLS}`}>
          <div />
          <div />
          <span>氏名</span>
          <span>所属課</span>
          <span>役職</span>
          <span className="text-right">回数(月平均)</span>
        </div>
      )}

      {/* Workerリスト */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
        {workers.length === 0 ? (
          <p className="text-[11px] text-gray-400 text-center py-4">
            対応者が登録されていません
          </p>
        ) : showAll ? (
          // 全表示モード: フィルタで除外されるWorkerを薄く表示
          workers.map((w) => (
            <WorkerCard
              key={w.id}
              worker={w}
              departments={departments}
              skillRanks={skillRanks}
              disabled={!availableIds.has(w.id)}
            />
          ))
        ) : (
          // スマートサジェストモード: 6カラムGrid表示 + スマートソート
          sortedAvailableWorkers.map((w) => {
            const statsItem = aggregateStatsMap.get(w.id);
            const slotStat = activeSlotType
              ? statsItem?.slot_stats.find((s) => s.slot_type === activeSlotType) ?? null
              : null;
            const positionName = statsItem?.position_name ?? null;
            const employmentTypeName =
              statsItem?.employment_type_name ??
              (w.employment_type_id
                ? (employmentTypeNameById.get(w.employment_type_id) ?? null)
                : null);
            const isNonDefaultEmployment =
              statsItem?.is_non_default_employment ?? w.is_special ?? false;

            return (
              <SmartSuggestRow
                key={w.id}
                worker={w}
                departments={departments}
                skillRanks={skillRanks}
                positionName={positionName}
                employmentTypeName={employmentTypeName}
                isNonDefaultEmployment={isNonDefaultEmployment}
                slotStats={
                  slotStat
                    ? { count: slotStat.count, monthlyAvg: slotStat.monthly_avg }
                    : null
                }
              />
            );
          })
        )}
      </div>

      {/* アクティブスロットなし時のヒント */}
      {!activeSlotType && (
        <div className="px-3 py-2 border-t border-gray-200">
          <p className="text-[10px] text-gray-400 text-center">
            枠をクリックしてアサインを開始
          </p>
        </div>
      )}
    </div>
  );
}
