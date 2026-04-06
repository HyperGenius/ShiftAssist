"use client";

import type { Department } from "@/types/department";
import type { SlotType } from "@/types/shiftRequirement";
import type { ShiftRulesConfig } from "@/types/shiftRules";
import type { TenantSkillRank } from "@/types/skillRank";
import type { Worker } from "@/types/worker";
import { useAvailableWorkers } from "@/hooks/useAvailableWorkers";
import { WorkerCard } from "./WorkerCard";

interface WorkerListPanelProps {
  workers: Worker[];
  departments: Department[];
  skillRanks: TenantSkillRank[];
  rules?: ShiftRulesConfig;
  /** 現在アクティブなスロットの種類（フィルタリングに使用） */
  activeSlotType: SlotType | null;
  /** 現在アクティブなスロットのアサイン済みWorkerID */
  activeAssignedWorkerIds: (string | null)[];
  /** 全表示モード（制約無視） */
  showAll: boolean;
  /** 全表示モード変更コールバック */
  onShowAllChange: (value: boolean) => void;
}

/**
 * シフトアサイン画面の右サイドパネルコンポーネント。
 * Workerの一覧をフィルタリングして表示し、各WorkerCardはドラッグ可能。
 */
export function WorkerListPanel({
  workers,
  departments,
  skillRanks,
  rules,
  activeSlotType,
  activeAssignedWorkerIds,
  showAll,
  onShowAllChange,
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

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* パネルヘッダー */}
      <div className="px-3 py-2 border-b border-gray-200">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            対応者リスト
          </h3>
          <span className="text-[10px] text-gray-400">
            {availableWorkers.length}/{totalWorkerCount}
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
          // スマートサジェストモード: 対象Workerのみ表示
          availableWorkers.map((w) => (
            <WorkerCard
              key={w.id}
              worker={w}
              departments={departments}
              skillRanks={skillRanks}
            />
          ))
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
