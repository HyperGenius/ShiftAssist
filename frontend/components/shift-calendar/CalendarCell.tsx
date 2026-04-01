"use client";

import type { Worker } from "@/types/worker";
import type { DayState, SlotType } from "@/types/shiftRequirement";
import type { DayType } from "@/utils/calendarUtils";
import { ShiftSlot } from "./ShiftSlot";

const DAY_NAMES = ["日", "月", "火", "水", "木", "金", "土"];

const DAYTIME_TYPES = new Set<SlotType>([
  "sat_day",
  "sun_hol_day",
  "long_hol_day",
]);
const NIGHTTIME_TYPES = new Set<SlotType>([
  "sat_night",
  "sun_hol_night",
  "long_hol_night",
  "weekday_night",
]);

interface CalendarCellProps {
  date: Date;
  dayType: DayType;
  isHoliday: boolean;
  holidayName?: string;
  dayState: DayState;
  workers: Worker[];
  onWorkerChange: (
    slotType: SlotType,
    index: number,
    workerId: string | null,
  ) => void;
}

/** 1日分のカレンダーセルコンポーネント */
export function CalendarCell({
  date,
  dayType,
  isHoliday,
  holidayName,
  dayState,
  workers,
  onWorkerChange,
}: CalendarCellProps) {
  const dayOfWeek = date.getDay();
  const dayNum = date.getDate();

  const cellBg =
    dayType === "saturday"
      ? "bg-blue-900/20 border-blue-700/40"
      : dayType === "sunday_holiday"
        ? "bg-red-900/20 border-red-700/40"
        : "bg-slate-800/30 border-slate-700/40";

  const dayColor =
    dayType === "saturday"
      ? "text-blue-300"
      : dayType === "sunday_holiday"
        ? "text-red-300"
        : "text-slate-200";

  const slotEntries = Object.entries(dayState) as [SlotType, DayState[string]][];
  const daytimeSlots = slotEntries.filter(([t]) => DAYTIME_TYPES.has(t));
  const nighttimeSlots = slotEntries.filter(([t]) => NIGHTTIME_TYPES.has(t));

  return (
    <div
      className={`border rounded-lg p-1.5 flex flex-col gap-1 min-h-[120px] ${cellBg}`}
    >
      {/* 日付ヘッダー */}
      <div className="flex items-center justify-between mb-0.5">
        <span className={`text-sm font-semibold ${dayColor}`}>{dayNum}</span>
        <span className="text-[10px] text-slate-500">
          {DAY_NAMES[dayOfWeek]}
        </span>
        {isHoliday && (
          <span className="text-[9px] text-red-400" title={holidayName}>
            🎌
          </span>
        )}
      </div>

      {/* 昼間スロット */}
      {daytimeSlots.length > 0 && (
        <div className="flex flex-col gap-1">
          <div className="text-[9px] text-slate-500 border-b border-slate-700/50 pb-0.5 text-center">
              昼間
            </div>
          {daytimeSlots.map(([slotType, slotState]) => (
            <ShiftSlot
              key={slotType}
              slotType={slotType}
              workerSelections={slotState.workerSelections}
              workers={workers}
              onWorkerChange={(idx, wid) => onWorkerChange(slotType, idx, wid)}
            />
          ))}
        </div>
      )}

      {/* 夜間スロット */}
      {nighttimeSlots.length > 0 && (
        <div className="flex flex-col gap-1">
          {daytimeSlots.length > 0 && (
            <div className="text-[9px] text-slate-500 border-b border-slate-700/50 pb-0.5 text-center mt-0.5">
              夜間
            </div>
          )}
          {nighttimeSlots.map(([slotType, slotState]) => (
            <ShiftSlot
              key={slotType}
              slotType={slotType}
              workerSelections={slotState.workerSelections}
              workers={workers}
              onWorkerChange={(idx, wid) => onWorkerChange(slotType, idx, wid)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
