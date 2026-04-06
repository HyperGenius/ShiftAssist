"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

import type { Department } from "@/types/department";
import type { TenantSkillRank } from "@/types/skillRank";
import type { Worker } from "@/types/worker";

/** 課IDごとの色クラスパレット（固定6色でサイクル） */
const DEPT_COLORS = [
  "bg-cyan-500/20 text-cyan-300 border-cyan-500/40",
  "bg-purple-500/20 text-purple-300 border-purple-500/40",
  "bg-green-500/20 text-green-300 border-green-500/40",
  "bg-orange-500/20 text-orange-300 border-orange-500/40",
  "bg-pink-500/20 text-pink-300 border-pink-500/40",
  "bg-indigo-500/20 text-indigo-300 border-indigo-500/40",
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
      className={[
        "flex items-center gap-1.5 px-2 py-1.5 rounded border text-xs select-none transition-all",
        disabled
          ? "opacity-40 cursor-not-allowed bg-slate-800/20 border-slate-700/30 text-slate-500"
          : isDragging
            ? "opacity-80 bg-slate-700/80 border-cyan-500/60 shadow-[0_0_12px_rgba(6,182,212,0.3)] cursor-grabbing z-50"
            : "bg-slate-800/60 border-slate-600/50 text-slate-200 cursor-grab hover:bg-slate-700/60 hover:border-slate-500/60",
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
        <span className="shrink-0 px-1 py-0.5 rounded border bg-yellow-500/20 text-yellow-300 border-yellow-500/40 text-[9px] font-bold">
          Ldr
        </span>
      )}

      {/* 特別雇用ラベル */}
      {worker.is_special && (
        <span className="shrink-0 px-1 py-0.5 rounded border bg-rose-500/20 text-rose-300 border-rose-500/40 text-[9px] font-medium">
          特別
        </span>
      )}
    </div>
  );
}
