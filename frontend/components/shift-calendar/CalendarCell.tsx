"use client";

import type { Department } from "@/types/department";
import type { Worker } from "@/types/worker";
import type { DayState, SlotType } from "@/types/shiftRequirement";
import type { TenantSkillRank } from "@/types/skillRank";
import type { DayType } from "@/utils/calendarUtils";
import type { ValidationViolation } from "@/utils/shiftValidators";
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
  dateStr: string;
  dayType: DayType;
  isHoliday: boolean;
  holidayName?: string;
  dayState: DayState;
  workers: Worker[];
  departments: Department[];
  skillRanks: TenantSkillRank[];
  /** スロットタイプ → バリデーション違反リスト */
  dayViolations?: Partial<Record<SlotType, ValidationViolation[]>>;
  /** ドラッグ中WorkerIDがアサイン可能かチェックする関数 */
  isWorkerAvailable: (workerId: string) => boolean;
  onWorkerChange: (
    slotType: SlotType,
    index: number,
    workerId: string | null,
  ) => void;
  onSlotFocus: (dateStr: string, slotType: SlotType) => void;
  readOnly?: boolean;
}

/** 1日分のカレンダーセルコンポーネント */
export function CalendarCell({
  date,
  dateStr,
  dayType,
  isHoliday,
  holidayName,
  dayState,
  workers,
  departments,
  skillRanks,
  dayViolations = {},
  isWorkerAvailable,
  onWorkerChange,
  onSlotFocus,
  readOnly = false,
}: CalendarCellProps) {
  const dayOfWeek = date.getDay();
  const dayNum = date.getDate();

  const cellBg =
    dayType === "saturday"
      ? "bg-blue-50 border-blue-200"
      : dayType === "sunday_holiday"
        ? "bg-red-50 border-red-200"
        : "bg-white border-gray-200";

  const dayColor =
    dayType === "saturday"
      ? "text-blue-600"
      : dayType === "sunday_holiday"
        ? "text-red-600"
        : "text-gray-800";

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
        <span className="text-[10px] text-gray-400">
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
          {daytimeSlots.map(([slotType, slotState]) => (
            <ShiftSlot
              key={slotType}
              dateStr={dateStr}
              slotType={slotType}
              workerSelections={slotState.workerSelections}
              workers={workers}
              departments={departments}
              skillRanks={skillRanks}
              violations={dayViolations[slotType] ?? []}
              isWorkerAvailable={isWorkerAvailable}
              onWorkerChange={(idx, wid) => onWorkerChange(slotType, idx, wid)}
              onSlotFocus={onSlotFocus}
              readOnly={readOnly}
            />
          ))}
        </div>
      )}

      {/* 夜間スロット */}
      {nighttimeSlots.length > 0 && (
        <div className="flex flex-col gap-1">
          {nighttimeSlots.map(([slotType, slotState]) => (
            <ShiftSlot
              key={slotType}
              dateStr={dateStr}
              slotType={slotType}
              workerSelections={slotState.workerSelections}
              workers={workers}
              departments={departments}
              skillRanks={skillRanks}
              violations={dayViolations[slotType] ?? []}
              isWorkerAvailable={isWorkerAvailable}
              onWorkerChange={(idx, wid) => onWorkerChange(slotType, idx, wid)}
              onSlotFocus={onSlotFocus}
              readOnly={readOnly}
            />
          ))}
        </div>
      )}
    </div>
  );
}
