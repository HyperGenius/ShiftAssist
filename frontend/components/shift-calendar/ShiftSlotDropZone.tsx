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
  /** クリックによるスロット選択コールバック（空きスロットのみ呼ばれる） */
  onSelectSlot?: () => void;
  /** このスロットが選択中かどうか（クリックアサインフロー用） */
  isSelected?: boolean;
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
  onSelectSlot,
  isSelected = false,
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
  // アサイン済みスロットへのドロップは禁止する
  const isOccupied = workerId !== null;
  const isAllowed = !activeDragWorkerId || (!isOccupied && isDropAllowed(activeDragWorkerId));

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
      onClick={(e) => {
        e.stopPropagation();
        onFocus();
        if (!isOccupied) {
          onSelectSlot?.();
        }
      }}
      className={[
        "group relative min-h-[26px] rounded border px-1.5 py-1 text-[10px] transition-all cursor-pointer",
        // 選択中スロット（クリックアサインフロー）
        isSelected && !isDragActive && "ring-2 ring-blue-500 ring-offset-1",
        // 通常状態: クリーンなモダンUI
        !isDragActive && "bg-white border-gray-200 hover:border-gray-300",
        // ドラッグ中: 禁止（制約違反 or アサイン済みスロット）
        showDropForbidden && "bg-red-50 border-red-500 cursor-no-drop",
        // ドラッグ中: ドロップ可能
        showDropReady && "bg-blue-50 border-blue-300 border-dashed",
        // ドラッグ中: ホバー中（ドロップ可）
        showDropActive && "bg-blue-100 border-blue-400 shadow-sm",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {assignedWorker ? (
        <>
          {/* アサイン済みWorker情報: 縦積みレイアウト */}
          <div className="flex flex-col min-w-0">
            {/* 1行目: 名前 + リーダーアイコン（pr-5は右上✕ボタン分のスペース） */}
            <div className="flex items-center gap-0.5 pr-5">
              <span className="text-gray-800 font-medium truncate">
                {assignedWorker.name}
              </span>
              {rank?.is_leader_eligible && (
                <span className="shrink-0 text-[8px] text-yellow-500">★</span>
              )}
            </div>
            {/* 2行目: 所属バッジ */}
            {dept && (
              <span className="mt-0.5 self-start text-[8px] px-1 rounded bg-gray-100 text-gray-500 border border-gray-200">
                {dept.name}
              </span>
            )}
          </div>
          {/* クリアボタン: ホバー時のみ表示 */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 focus:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
            aria-label="アサイン解除"
          >
            ✕
          </button>
        </>
      ) : (
        <div className="flex items-center justify-center min-h-[18px]">
          <span
            className={[
              "text-gray-400 text-center",
              showDropActive && "text-blue-500",
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
        </div>
      )}
    </div>
  );
}
