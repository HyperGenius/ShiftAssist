"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { CalendarCell } from "./CalendarCell";
import { useShiftRequirements } from "@/hooks/useShiftRequirements";
import { useWorkers } from "@/hooks/useWorkers";
import type {
  CalendarState,
  SlotState,
  SlotType,
  ShiftRequirementCreate,
} from "@/types/shiftRequirement";
import type { Department } from "@/types/department";
import {
  getDayType,
  getDefaultSlotTypes,
  getCalendarGrid,
  getHolidayMap,
  toDateStr,
  isHoliday,
  type DayType,
} from "@/utils/calendarUtils";

const WEEK_HEADERS = ["日", "月", "火", "水", "木", "金", "土"];
const DEFAULT_HEADCOUNT = 2;

interface ShiftCalendarProps {
  department: Department;
}

/** 月間シフト枠カレンダーコンポーネント */
export function ShiftCalendar({ department }: ShiftCalendarProps) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [calendarState, setCalendarState] = useState<CalendarState>({});
  const [isSaving, setIsSaving] = useState(false);

  const { shiftRequirements, isLoading, createShiftRequirement, updateShiftRequirement } =
    useShiftRequirements();
  const { workers } = useWorkers();

  const holidayMap = useMemo(() => getHolidayMap(year, month), [year, month]);
  const holidaySet = useMemo(() => new Set(holidayMap.keys()), [holidayMap]);
  const calendarGrid = useMemo(
    () => getCalendarGrid(year, month),
    [year, month],
  );

  /** 月のシフト枠データをカレンダーステートに変換して初期化する */
  useEffect(() => {
    const newState: CalendarState = {};

    // グリッド内の全日付に対してデフォルトステートを作成
    for (const date of calendarGrid) {
      if (!date) continue;
      const dateStr = toDateStr(date);
      const dayType: DayType = getDayType(date, dateStr, holidaySet);
      const slotTypes = getDefaultSlotTypes(dayType);
      newState[dateStr] = {};
      for (const slotType of slotTypes) {
        newState[dateStr][slotType] = {
          slot_type: slotType,
          required_headcount: DEFAULT_HEADCOUNT,
          workerSelections: Array(DEFAULT_HEADCOUNT).fill(null) as null[],
          isDirty: false,
        };
      }
    }

    // バックエンドから取得したシフト枠データで上書き
    const monthPrefix = `${year}-${String(month).padStart(2, "0")}`;
    for (const req of shiftRequirements) {
      if (
        !req.shift_date.startsWith(monthPrefix) ||
        req.department_id !== department.id
      )
        continue;
      const dateStr = req.shift_date;
      if (!newState[dateStr]) continue;
      const headcount = req.required_headcount;
      newState[dateStr][req.slot_type] = {
        requirementId: req.id,
        slot_type: req.slot_type,
        required_headcount: headcount,
        workerSelections: Array(headcount).fill(null) as null[],
        isDirty: false,
      };
    }

    setCalendarState(newState);
  }, [shiftRequirements, calendarGrid, holidaySet, year, month, department.id]);

  /** ワーカー選択変更ハンドラ */
  const handleWorkerChange = useCallback(
    (dateStr: string, slotType: SlotType, index: number, workerId: string | null) => {
      setCalendarState((prev) => {
        const dayState = prev[dateStr];
        if (!dayState) return prev;
        const slotState = dayState[slotType];
        if (!slotState) return prev;
        const newSelections = [...slotState.workerSelections];
        newSelections[index] = workerId;
        return {
          ...prev,
          [dateStr]: {
            ...dayState,
            [slotType]: {
              ...slotState,
              workerSelections: newSelections,
              isDirty: true,
            },
          },
        };
      });
    },
    [],
  );

  /** 保存ハンドラ */
  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      const savePromises: Promise<unknown>[] = [];
      for (const [dateStr, dayState] of Object.entries(calendarState)) {
        for (const [, slotState] of Object.entries(dayState) as [string, SlotState][]) {
          if (!slotState.isDirty) continue;
          if (slotState.requirementId) {
            // 既存データの更新
            savePromises.push(
              updateShiftRequirement(slotState.requirementId, {
                required_headcount: slotState.required_headcount,
              }),
            );
          } else {
            // 新規作成
            const payload: ShiftRequirementCreate = {
              department_id: department.id,
              shift_date: dateStr,
              slot_type: slotState.slot_type,
              required_headcount: slotState.required_headcount,
            };
            savePromises.push(createShiftRequirement(payload));
          }
        }
      }
      await Promise.all(savePromises);
      toast.success("シフト枠を保存しました");
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setIsSaving(false);
    }
  }, [calendarState, createShiftRequirement, updateShiftRequirement, department.id]);

  const prevMonth = useCallback(() => {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
  }, [month]);

  const nextMonth = useCallback(() => {
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
  }, [month]);

  const hasDirtySlots = useMemo(() => {
    for (const dayState of Object.values(calendarState)) {
      for (const slotState of Object.values(dayState)) {
        if ((slotState as SlotState).isDirty) return true;
      }
    }
    return false;
  }, [calendarState]);

  return (
    <SciFiPanel className="p-4">
      {/* ヘッダー：月ナビゲーション＆保存ボタン */}
      <div className="flex items-center justify-between mb-4">
        <SciFiButton variant="secondary" size="sm" onClick={prevMonth}>
          &lt;&lt; 前月
        </SciFiButton>
        <h2 className="text-base font-semibold tracking-widest text-cyan-300">
          {year}年 {month}月
          <span className="ml-2 text-xs text-slate-400 normal-case">
            {department.name}
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <SciFiButton variant="secondary" size="sm" onClick={nextMonth}>
            翌月 &gt;&gt;
          </SciFiButton>
          <SciFiButton
            variant="primary"
            size="sm"
            onClick={handleSave}
            loading={isSaving}
            disabled={!hasDirtySlots}
          >
            保存
          </SciFiButton>
        </div>
      </div>

      {/* ローディング状態 */}
      {isLoading && (
        <div className="flex items-center justify-center py-12 text-slate-400 text-sm">
          <span className="animate-spin h-4 w-4 border-2 border-cyan-500 border-t-transparent rounded-full mr-2" />
          読み込み中...
        </div>
      )}

      {/* カレンダーグリッド */}
      {!isLoading && (
        <>
          {/* 曜日ヘッダー */}
          <div className="grid grid-cols-7 gap-1 mb-1">
            {WEEK_HEADERS.map((h, i) => (
              <div
                key={h}
                className={`text-center text-xs py-1 font-medium tracking-widest ${
                  i === 0
                    ? "text-red-400"
                    : i === 6
                      ? "text-blue-400"
                      : "text-slate-400"
                }`}
              >
                {h}
              </div>
            ))}
          </div>

          {/* カレンダーセル */}
          <div className="grid grid-cols-7 gap-1">
            {calendarGrid.map((date, idx) => {
              if (!date) {
                return <div key={`empty-${idx}`} className="min-h-[120px]" />;
              }
              const dateStr = toDateStr(date);
              const holidayFlag = isHoliday(dateStr, holidaySet);
              const holidayName = holidayMap.get(dateStr);
              const dayType = getDayType(date, dateStr, holidaySet);
              const dayState = calendarState[dateStr] ?? {};

              return (
                <CalendarCell
                  key={dateStr}
                  date={date}
                  dayType={dayType}
                  isHoliday={holidayFlag}
                  holidayName={holidayName}
                  dayState={dayState}
                  workers={workers}
                  onWorkerChange={(slotType, idx2, wid) =>
                    handleWorkerChange(dateStr, slotType, idx2, wid)
                  }
                />
              );
            })}
          </div>

          {/* 凡例 */}
          <div className="mt-4 flex items-center gap-4 text-[10px] text-slate-500">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-slate-800/30 border border-slate-700/40 inline-block" />
              平日
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-blue-900/20 border border-blue-700/40 inline-block" />
              土曜日
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-red-900/20 border border-red-700/40 inline-block" />
              日曜・祝日
            </span>
            <span className="flex items-center gap-1">🎌 祝日</span>
          </div>
        </>
      )}
    </SciFiPanel>
  );
}
