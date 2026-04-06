"use client";

import { useDndContext, useDroppable } from "@dnd-kit/core";

import type { Department } from "@/types/department";
import type { TenantSkillRank } from "@/types/skillRank";
import type { Worker } from "@/types/worker";

/** ドロップ可能な1スロット枠のIDプレフィックス */
export const DROP_ZONE_ID_PREFIX = "slot-drop:";

/** ドロップゾーンIDを生成する */
export function buildDropZoneId(
  dateStr: string,
  slotType: string,
  index: number,
): string {
  return `${DROP_ZONE_ID_PREFIX}${dateStr}__${slotType}__${index}`;
}

/** ドロップゾーンIDをパースする */
export function parseDropZoneId(id: string): {
  dateStr: string;
  slotType: string;
  index: number;
} | null {
  if (!id.startsWith(DROP_ZONE_ID_PREFIX)) return null;
  const parts = id.slice(DROP_ZONE_ID_PREFIX.length).split("__");
  if (parts.length !== 3) return null;
  return {
    dateStr: parts[0],
    slotType: parts[1],
    index: parseInt(parts[2], 10),
  };
}

interface ShiftSlotDropZoneProps {
  dateStr: string;
  slotType: string;
  index: number;
  workerId: string | null;
  workers: Worker[];
  departments: Department[];
  skillRanks: TenantSkillRank[];
  /** ドロップ可否を判定する関数（WorkerIDを受け取りbooleanを返す） */
  isDropAllowed: (workerId: string) => boolean;
  onClear: () => void;
  onFocus: () => void;
}

/**
 * カレンダー上の1スロット1枠分のドロップターゲット。
 * 現在アサインされているWorkerを表示し、クリアボタンを持つ。
 */
export function ShiftSlotDropZone({
  dateStr,
  slotType,
  index,
  workerId,
  workers,
  departments,
  skillRanks,
  isDropAllowed,
  onClear,
  onFocus,
}: ShiftSlotDropZoneProps) {
  const dropId = buildDropZoneId(dateStr, slotType, index);
  const { isOver, setNodeRef } = useDroppable({ id: dropId });

  // DnDコンテキストからアクティブなドラッグ情報を取得
  const { active } = useDndContext();
  const activeDragWorkerId =
    typeof active?.data?.current?.workerId === "string"
      ? active.data.current.workerId
      : null;
  const isDragActive = activeDragWorkerId !== null;
  const isAllowed = !activeDragWorkerId || isDropAllowed(activeDragWorkerId);

  const assignedWorker = workerId
    ? workers.find((w) => w.id === workerId)
    : null;

  const dept = assignedWorker
    ? departments.find((d) => d.id === assignedWorker.department_id)
    : null;
  const rank = assignedWorker
    ? skillRanks.find((r) => r.id === assignedWorker.skill_rank_id)
    : null;

  // ドラッグ中のドロップ可否表示
  const showDropForbidden = isDragActive && !isAllowed;
  const showDropReady = isDragActive && isAllowed && !isOver;
  const showDropActive = isDragActive && isAllowed && isOver;

  return (
    <div
      ref={setNodeRef}
      onClick={onFocus}
      className={[
        "relative min-h-[26px] rounded border px-1.5 py-1 text-[10px] transition-all cursor-pointer flex items-center gap-1",
        // 通常状態
        !isDragActive && "bg-slate-800/40 border-slate-600/40 hover:border-slate-500/60",
        // ドラッグ中: 禁止
        showDropForbidden && "bg-red-900/20 border-red-500/40 cursor-no-drop",
        // ドラッグ中: ドロップ可能
        showDropReady && "bg-cyan-900/20 border-cyan-500/40 border-dashed",
        // ドラッグ中: ホバー中（ドロップ可）
        showDropActive && "bg-cyan-500/20 border-cyan-400/70 shadow-[0_0_8px_rgba(6,182,212,0.4)]",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {assignedWorker ? (
        <>
          {/* アサイン済みWorker情報 */}
          <span className="text-slate-200 font-medium truncate flex-1">
            {assignedWorker.name}
          </span>
          {dept && (
            <span className="shrink-0 text-[8px] px-0.5 rounded bg-slate-700/60 text-slate-400">
              {dept.name}
            </span>
          )}
          {rank?.is_leader_eligible && (
            <span className="shrink-0 text-[8px] text-yellow-400">★</span>
          )}
          {/* クリアボタン */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="shrink-0 text-slate-500 hover:text-red-400 transition-colors ml-0.5"
            aria-label="アサイン解除"
          >
            ✕
          </button>
        </>
      ) : (
        <span
          className={[
            "text-slate-600 flex-1 text-center",
            showDropActive && "text-cyan-400",
            showDropForbidden && "text-red-400",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {showDropForbidden
            ? "⊘ 不可"
            : showDropActive
              ? "ここへドロップ"
              : "---"}
        </span>
      )}
    </div>
  );
}

