"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

import type { Department } from "@/types/department";
import type { TenantSkillRank } from "@/types/skillRank";
import type { Worker } from "@/types/worker";

/** 課IDごとの色クラスパレット（固定6色でサイクル） */
const DEPT_COLORS = [
  "bg-blue-50 text-blue-700 border-blue-200",
  "bg-purple-50 text-purple-700 border-purple-200",
  "bg-green-50 text-green-700 border-green-200",
  "bg-orange-50 text-orange-700 border-orange-200",
  "bg-pink-50 text-pink-700 border-pink-200",
  "bg-indigo-50 text-indigo-700 border-indigo-200",
];

function getDeptColorClass(deptId: string, departments: Department[]): string {
  const idx = departments.findIndex((d) => d.id === deptId);
  return DEPT_COLORS[(idx >= 0 ? idx : 0) % DEPT_COLORS.length];
}

interface WorkerCardProps {
  worker: Worker;
  departments: Department[];
  skillRanks: TenantSkillRank[];
  /** ドラッグ不可（フィルタで除外されている場合） */
  disabled?: boolean;
  /** クリックアサインコールバック（選択中スロットへのアサイン） */
  onWorkerClick?: (workerId: string) => void;
}

/**
 * サイドパネルに表示するドラッグ可能なWorkerカード。
 * 名前・所属課バッジ・リーダーバッジ・特別雇用ラベルを表示する。
 */
export function WorkerCard({
  worker,
  departments,
  skillRanks,
  disabled = false,
  onWorkerClick,
}: WorkerCardProps) {
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
  const deptColor = getDeptColorClass(worker.department_id, departments);

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={(e) => {
        if (!isDragging && !disabled && onWorkerClick) {
          e.stopPropagation();
          onWorkerClick(worker.id);
        }
      }}
      className={[
        "flex items-center gap-1.5 px-2 py-1.5 rounded border text-xs select-none transition-all",
        disabled
          ? "opacity-40 cursor-not-allowed bg-gray-50 border-gray-200 text-gray-400"
          : isDragging
            ? "opacity-80 bg-gray-100 border-blue-400 shadow-sm cursor-grabbing z-50"
            : onWorkerClick
              ? "bg-white border-gray-200 text-gray-700 cursor-pointer hover:bg-blue-50 hover:border-blue-300"
              : "bg-white border-gray-200 text-gray-700 cursor-grab hover:bg-gray-50 hover:border-gray-300",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* 名前 */}
      <span className="font-medium truncate min-w-0 flex-1">{worker.name}</span>

      {/* 所属課バッジ */}
      {dept && (
        <span
          className={`shrink-0 px-1 py-0.5 rounded border text-[9px] font-medium ${deptColor}`}
        >
          {dept.name}
        </span>
      )}

      {/* リーダーバッジ */}
      {rank?.is_leader_eligible && (
        <span className="shrink-0 px-1 py-0.5 rounded border bg-yellow-50 text-yellow-700 border-yellow-200 text-[9px] font-bold">
          Ldr
        </span>
      )}

      {/* 特別雇用ラベル */}
      {worker.is_special && (
        <span className="shrink-0 px-1 py-0.5 rounded border bg-rose-50 text-rose-700 border-rose-200 text-[9px] font-medium">
          特別
        </span>
      )}
    </div>
  );
}
