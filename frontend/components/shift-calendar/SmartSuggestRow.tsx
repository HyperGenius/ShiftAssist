"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

import type { Department } from "@/types/department";
import type { TenantSkillRank } from "@/types/skillRank";
import type { Worker } from "@/types/worker";

/** スマートサジェスト行の CSS Grid カラム定義 */
export const SMART_SUGGEST_GRID_COLS = "grid-cols-[18px_20px_auto_60px_60px_76px]";

interface SmartSuggestRowProps {
  worker: Worker;
  departments: Department[];
  skillRanks: TenantSkillRank[];
  /** 役職名（position_id に紐づく名称） */
  positionName?: string | null;
  /** 雇用形態名（employment_type_id に紐づく名称） */
  employmentTypeName?: string | null;
  /** 雇用形態が非デフォルトまたは is_special の場合 true */
  isNonDefaultEmployment?: boolean;
  /** 対象スロットの集計情報 */
  slotStats?: { count: number; monthlyAvg: number } | null;
  /** ドラッグ不可（フィルタで除外されている場合） */
  disabled?: boolean;
}

/**
 * スマートサジェスト用のドラッグ可能な行コンポーネント。
 * 6カラムGrid（リーダーバッジ / 雇用形態バッジ / 氏名 / 所属課 / 役職 / 集計情報）を表示する。
 */
export function SmartSuggestRow({
  worker,
  departments,
  skillRanks,
  positionName,
  employmentTypeName,
  isNonDefaultEmployment,
  slotStats,
  disabled = false,
}: SmartSuggestRowProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: worker.id,
      data: { workerId: worker.id },
      disabled,
    });

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined;

  const dept = departments.find((d) => d.id === worker.department_id);
  const rank = skillRanks.find((r) => r.id === worker.skill_rank_id);
  const isLeader = rank?.is_leader_eligible ?? false;

  const statsText = slotStats
    ? `${slotStats.count}(${slotStats.monthlyAvg.toFixed(1)}/月)`
    : "—";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={[
        "grid items-center gap-x-1 px-1.5 py-1 rounded border text-xs select-none transition-all",
        SMART_SUGGEST_GRID_COLS,
        disabled
          ? "opacity-40 cursor-not-allowed bg-gray-50 border-gray-200 text-gray-400"
          : isDragging
            ? "opacity-80 bg-gray-100 border-blue-400 shadow-sm cursor-grabbing z-50"
            : "bg-white border-gray-200 text-gray-700 cursor-grab hover:bg-gray-50 hover:border-gray-300",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* 列1: リーダーバッジ */}
      <div className="flex justify-center">
        {isLeader ? (
          <span className="px-0.5 rounded border bg-yellow-50 text-yellow-700 border-yellow-200 text-[9px] font-bold leading-tight">
            L
          </span>
        ) : (
          <span className="inline-block w-[14px]" />
        )}
      </div>

      {/* 列2: 雇用形態バッジ */}
      <div className="flex justify-center">
        {isNonDefaultEmployment && employmentTypeName ? (
          <span
            className="px-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 text-[9px] font-medium leading-tight truncate max-w-full"
            title={employmentTypeName}
            aria-label={`雇用形態: ${employmentTypeName}`}
          >
            {employmentTypeName.slice(0, 2)}
          </span>
        ) : (
          <span className="inline-block w-[14px]" />
        )}
      </div>

      {/* 列3: 氏名 */}
      <span className="font-medium whitespace-nowrap">{worker.name}</span>

      {/* 列4: 所属課 */}
      <span
        className="truncate text-gray-500 text-[10px]"
        title={dept?.name ?? ""}
      >
        {dept?.name ?? ""}
      </span>

      {/* 列5: 役職 */}
      <span
        className="truncate text-gray-500 text-[10px]"
        title={positionName ?? ""}
      >
        {positionName ?? ""}
      </span>

      {/* 列6: 集計情報 */}
      <span className="text-right text-gray-400 text-[10px] whitespace-nowrap">
        {statsText}
      </span>
    </div>
  );
}
