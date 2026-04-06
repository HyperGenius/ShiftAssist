"use client";

import type { Department } from "@/types/department";
import type { Worker } from "@/types/worker";
import type { SlotType } from "@/types/shiftRequirement";
import { SLOT_TYPE_LABELS } from "@/types/shiftRequirement";
import type { TenantSkillRank } from "@/types/skillRank";
import type { ValidationViolation } from "@/utils/shiftValidators";
import { ValidationBadge } from "@/components/ui/ValidationBadge";
import { ShiftSlotDropZone } from "./ShiftSlotDropZone";

interface ShiftSlotProps {
  dateStr: string;
  slotType: SlotType;
  workerSelections: (string | null)[];
  workers: Worker[];
  departments: Department[];
  skillRanks: TenantSkillRank[];
  violations?: ValidationViolation[];
  /** ドラッグ中WorkerIDがアサイン可能かチェックする関数 */
  isWorkerAvailable: (workerId: string) => boolean;
  /** フォーカス時（スロット選択）コールバック */
  onSlotFocus: (dateStr: string, slotType: SlotType) => void;
  onWorkerChange: (index: number, workerId: string | null) => void;
}

/** 1スロット分のコンポーネント（DnDドロップゾーン） */
export function ShiftSlot({
  dateStr,
  slotType,
  workerSelections,
  workers,
  departments,
  skillRanks,
  violations = [],
  isWorkerAvailable,
  onSlotFocus,
  onWorkerChange,
}: ShiftSlotProps) {
  const label = SLOT_TYPE_LABELS[slotType];
  const hasError = violations.some((v) => v.severity === "error");
  const hasWarning = violations.some((v) => v.severity === "warning");

  const containerBorderClass = hasError
    ? "border-red-400"
    : hasWarning
      ? "border-yellow-400"
      : "border-gray-200";

  return (
    <div className={`flex flex-col gap-1 rounded border p-1 ${containerBorderClass}`}>
      <div className="flex items-center justify-center gap-1">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider text-center">
          {label}
        </span>
        <ValidationBadge violations={violations} />
      </div>
      {workerSelections.map((workerId, idx) => (
        <ShiftSlotDropZone
          key={idx}
          dateStr={dateStr}
          slotType={slotType}
          index={idx}
          workerId={workerId}
          workers={workers}
          departments={departments}
          skillRanks={skillRanks}
          isDropAllowed={isWorkerAvailable}
          onClear={() => onWorkerChange(idx, null)}
          onFocus={() => onSlotFocus(dateStr, slotType)}
        />
      ))}
    </div>
  );
}
