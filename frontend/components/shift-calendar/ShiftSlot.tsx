"use client";

import type { Worker } from "@/types/worker";
import type { SlotType } from "@/types/shiftRequirement";
import { SLOT_TYPE_LABELS } from "@/types/shiftRequirement";
import type { ValidationViolation } from "@/utils/shiftValidators";
import { ValidationBadge } from "@/components/ui/ValidationBadge";

interface ShiftSlotProps {
  slotType: SlotType;
  workerSelections: (string | null)[];
  workers: Worker[];
  violations?: ValidationViolation[];
  onWorkerChange: (index: number, workerId: string | null) => void;
}

/** 1スロット分のコンポーネント（ワーカー選択プルダウンを含む） */
export function ShiftSlot({
  slotType,
  workerSelections,
  workers,
  violations = [],
  onWorkerChange,
}: ShiftSlotProps) {
  const label = SLOT_TYPE_LABELS[slotType];
  const hasError = violations.some((v) => v.severity === "error");
  const hasWarning = violations.some((v) => v.severity === "warning");

  const selectBorderClass =
    hasError
      ? "border-red-500/70 focus:ring-red-500/70 focus:border-red-500/70"
      : hasWarning
        ? "border-yellow-500/70 focus:ring-yellow-500/70 focus:border-yellow-500/70"
        : "border-slate-600/50 focus:ring-cyan-500/70 focus:border-cyan-500/70";

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-center gap-1">
        <span className="text-[10px] text-slate-400 uppercase tracking-wider text-center">
          {label}
        </span>
        <ValidationBadge violations={violations} />
      </div>
      {workerSelections.map((workerId, idx) => (
        <select
          key={idx}
          value={workerId ?? ""}
          onChange={(e) =>
            onWorkerChange(idx, e.target.value === "" ? null : e.target.value)
          }
          className={`bg-slate-800/60 border rounded px-1.5 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 transition-colors w-full ${selectBorderClass}`}
          aria-label={`${label} スロット ${idx + 1}`}
        >
          <option value="">---</option>
          {workers.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      ))}
    </div>
  );
}
