"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { CalendarCell } from "./CalendarCell";
import { OverrideConfirmDialog } from "./OverrideConfirmDialog";
import { WorkerCard } from "./WorkerCard";
import { WorkerListPanel } from "./WorkerListPanel";
import { parseDropZoneId } from "./ShiftSlotDropZone";
import { YearMonthPicker } from "./YearMonthPicker";
import { useShiftRequirements } from "@/hooks/useShiftRequirements";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import { useWorkers } from "@/hooks/useWorkers";
import { useDepartments } from "@/hooks/useDepartments";
import { useAvailableWorkers } from "@/hooks/useAvailableWorkers";
import { useShiftRules } from "@/hooks/useShiftRules";
import { useValidationContext } from "@/hooks/useValidationContext";
import { useAggregateStats } from "@/hooks/useAggregateStats";
import { useEmploymentTypes } from "@/hooks/useEmploymentTypes";
import { useWorkerStats } from "@/hooks/useWorkerStats";
import type {
  CalendarState,
  SlotState,
  SlotType,
  ShiftRequirementCreate,
} from "@/types/shiftRequirement";
import type { Department } from "@/types/department";
import type { ShiftPlanDetail } from "@/types/shiftPlan";
import { useShiftValidation, buildSlotKey } from "@/hooks/useShiftValidation";
import type { ValidationViolation } from "@/utils/shiftValidators";
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
  /** 表示する年（URLから渡される制御値） */
  year: number;
  /** 表示する月（URLから渡される制御値） */
  month: number;
  /** 過去インポートデータ。指定時はそのデータでカレンダーを初期化する */
  pastPlan?: ShiftPlanDetail | null;
  /** true の場合、編集・保存操作を無効化する */
  readOnly?: boolean;
  /** 年月切り替え時のコールバック（URL更新など上位で処理） */
  onYearMonthChange: (year: number, month: number) => void;
}

/** 月間シフト枠カレンダーコンポーネント */
export function ShiftCalendar({ department, year, month, pastPlan, readOnly = false, onYearMonthChange }: ShiftCalendarProps) {
  const [calendarState, setCalendarState] = useState<CalendarState>({});
  const [isSaving, setIsSaving] = useState(false);
  const [showOverrideDialog, setShowOverrideDialog] = useState(false);

  // アクティブスロット（サイドパネルのフィルタリングに使用）
  const [activeSlot, setActiveSlot] = useState<{
    dateStr: string;
    slotType: SlotType;
  } | null>(null);

  // DnD オーバーライドモード
  const [showAll, setShowAll] = useState(false);

  // ドラッグ中のWorkerID
  const [draggingWorkerId, setDraggingWorkerId] = useState<string | null>(null);

  const { shiftRequirements, isLoading, createShiftRequirement, updateShiftRequirement, saveAssignments } =
    useShiftRequirements({ year, month });
  const { workers } = useWorkers();
  const { skillRanks } = useSkillRanks();
  const { departments } = useDepartments();
  const { rules } = useShiftRules();

  // 月跨ぎの min_interval_days チェック用に前月バッファを start_date として渡す
  const targetYearMonth = `${year}-${String(month).padStart(2, "0")}`;

  // 集計データ（スマートサジェストのソートと集計情報表示に使用）
  const { aggregateStats, isLoading: isAggregateStatsLoading } = useAggregateStats(targetYearMonth);
  const { employmentTypes } = useEmploymentTypes();
  const { stats: workerStatsData } = useWorkerStats();
  const validationStartDate = useMemo(() => {
    const minIntervalDays = rules.shift_rules?.min_interval_days ?? 10;
    const monthStart = new Date(year, month - 1, 1);
    const bufferStart = new Date(monthStart);
    bufferStart.setDate(bufferStart.getDate() - (minIntervalDays - 1));
    return bufferStart.toISOString().slice(0, 10); // YYYY-MM-DD
  }, [year, month, rules.shift_rules?.min_interval_days]);

  const { validationContext } = useValidationContext(targetYearMonth, validationStartDate);

  // 前月の直近シフト日付マップ（workerId → last_shift_date）
  const prevMonthDatesByWorker = useMemo<Record<string, string | null>>(() => {
    const stats = validationContext?.worker_stats;
    if (!stats || stats.length === 0) return {};
    return Object.fromEntries(stats.map((s) => [s.worker_id, s.last_shift_date]));
  }, [validationContext?.worker_stats]);

  // 年間シフト回数上限設定
  const annualLimits = rules.warnings?.annual_shift_limits;

  // シフト最小間隔（日数）
  const minIntervalDays = rules.shift_rules?.min_interval_days ?? 10;

  // 雇用形態マップ（employment_type_id → EmploymentType）
  const employmentTypeMap = useMemo(
    () => new Map(employmentTypes.map((et) => [et.id, et])),
    [employmentTypes],
  );

  const validationMap = useShiftValidation(
    calendarState,
    workers,
    rules.shift_rules,
    skillRanks,
    validationContext?.worker_stats ?? [],
    /* annualWorkerStats= */ undefined,
    /* annualLimits= */ undefined,
    employmentTypes,
  );

  const holidayMap = useMemo(() => getHolidayMap(year, month), [year, month]);
  const holidaySet = useMemo(() => new Set(holidayMap.keys()), [holidayMap]);
  const calendarGrid = useMemo(
    () => getCalendarGrid(year, month),
    [year, month],
  );

  // アクティブスロットの現在アサイン済みWorkerID一覧
  const activeAssignedWorkerIds = useMemo<(string | null)[]>(() => {
    if (!activeSlot) return [];
    return (
      calendarState[activeSlot.dateStr]?.[activeSlot.slotType]
        ?.workerSelections ?? []
    );
  }, [activeSlot, calendarState]);

  // アサイン可能なWorker一覧（サイドパネル＆ドロップゾーンの許可判定に使用）
  const { isWorkerAvailable } = useAvailableWorkers({
    workers,
    skillRanks,
    rules: undefined,
    slotType: activeSlot?.slotType ?? null,
    assignedWorkerIds: activeAssignedWorkerIds,
    showAll,
    workerStats: workerStatsData?.items,
    annualLimits,
    calendarState,
    currentDateStr: activeSlot?.dateStr,
    minIntervalDays,
    prevMonthDatesByWorker,
    employmentTypeMap,
  });

  // DnDセンサー設定
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 5 } }),
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

    if (pastPlan) {
      // 過去プランデータでカレンダーを上書きする
      const monthPrefix = `${year}-${String(month).padStart(2, "0")}`;
      for (const slot of pastPlan.slots) {
        const dateStr = slot.date.slice(0, 10); // ISO datetime から YYYY-MM-DD を抽出
        if (!dateStr.startsWith(monthPrefix)) continue;
        if (!newState[dateStr]) continue;
        const workerIds = slot.assignments.map((a) => a.worker_id);
        newState[dateStr][slot.slot_type as SlotType] = {
          slot_type: slot.slot_type as SlotType,
          required_headcount: workerIds.length || DEFAULT_HEADCOUNT,
          workerSelections: workerIds.length > 0 ? workerIds : Array(DEFAULT_HEADCOUNT).fill(null) as null[],
          isDirty: false,
        };
      }
    } else {
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

        // 保存済みのワーカー選択を復元する
        const savedWorkerIds = req.assignments.map((a) => a.worker_id);
        const workerSelections: (string | null)[] = Array(headcount).fill(null) as null[];
        for (let i = 0; i < Math.min(savedWorkerIds.length, headcount); i++) {
          workerSelections[i] = savedWorkerIds[i];
        }

        newState[dateStr][req.slot_type] = {
          requirementId: req.id,
          slot_type: req.slot_type,
          required_headcount: headcount,
          workerSelections,
          isDirty: false,
        };
      }
    }

    setCalendarState(newState);
  }, [shiftRequirements, pastPlan, calendarGrid, holidaySet, year, month, department.id]);

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

  /** スロットフォーカスハンドラ（サイドパネルフィルタリング更新） */
  const handleSlotFocus = useCallback((dateStr: string, slotType: SlotType) => {
    setActiveSlot({ dateStr, slotType });
  }, []);

  /** DnD開始ハンドラ */
  const handleDragStart = useCallback((event: DragStartEvent) => {
    const workerId =
      typeof event.active.data.current?.workerId === "string"
        ? event.active.data.current.workerId
        : null;
    setDraggingWorkerId(workerId);
  }, []);

  /** DnD終了ハンドラ */
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setDraggingWorkerId(null);
      const { active, over } = event;
      if (!over) return;

      const workerId =
        typeof active.data.current?.workerId === "string"
          ? active.data.current.workerId
          : null;
      if (!workerId) return;

      const parsed = parseDropZoneId(String(over.id));
      if (!parsed) return;

      const { dateStr, slotType, index } = parsed;

      // ルール違反チェック（showAll時に警告表示）
      if (showAll && !isWorkerAvailable(workerId)) {
        toast.warning("制約違反のアサインです。is_manual_override=true として保存されます。");
      }

      handleWorkerChange(dateStr, slotType as SlotType, index, workerId);
      // ドロップ先スロットをアクティブに設定
      setActiveSlot({ dateStr, slotType: slotType as SlotType });
    },
    [handleWorkerChange, isWorkerAvailable, showAll],
  );

  /** 実際の保存処理（バリデーションチェック後に呼ばれる） */
  const executeSave = useCallback(async (isManualOverride: boolean) => {
    setIsSaving(true);
    try {
      const savePromises: Promise<unknown>[] = [];
      for (const [dateStr, dayState] of Object.entries(calendarState)) {
        for (const [, slotState] of Object.entries(dayState) as [string, SlotState][]) {
          if (!slotState.isDirty) continue;

          const workerIds = slotState.workerSelections.filter(
            (id): id is string => id !== null,
          );

          if (slotState.requirementId) {
            // 既存データの更新
            const reqId = slotState.requirementId;
            savePromises.push(
              updateShiftRequirement(reqId, {
                required_headcount: slotState.required_headcount,
              }).then(() =>
                saveAssignments(reqId, {
                  worker_ids: workerIds,
                  is_manual_override: isManualOverride,
                }),
              ),
            );
          } else {
            // 新規作成してからアサインを保存
            const payload: ShiftRequirementCreate = {
              department_id: department.id,
              shift_date: dateStr,
              slot_type: slotState.slot_type,
              required_headcount: slotState.required_headcount,
            };
            savePromises.push(
              createShiftRequirement(payload).then((created) =>
                saveAssignments(created.id, {
                  worker_ids: workerIds,
                  is_manual_override: isManualOverride,
                }),
              ),
            );
          }
        }
      }
      await Promise.all(savePromises);
      toast.success(
        isManualOverride
          ? "シフト枠を強制保存しました（is_manual_override=true）"
          : "シフト枠を保存しました",
      );
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setIsSaving(false);
    }
  }, [calendarState, createShiftRequirement, updateShiftRequirement, saveAssignments, department.id]);

  /** 保存ハンドラ（バリデーションチェックを行い必要に応じてダイアログを表示） */
  const handleSave = useCallback(() => {
    const hasViolations = Object.keys(validationMap).length > 0;
    if (hasViolations) {
      // バリデーション違反があればオーバーライド確認ダイアログを表示
      setShowOverrideDialog(true);
    } else {
      // 違反なしならそのまま保存
      void executeSave(false);
    }
  }, [validationMap, executeSave]);

  /** ダイアログでキャンセルが押された場合 */
  const handleOverrideCancel = useCallback(() => {
    setShowOverrideDialog(false);
  }, []);

  /** ダイアログで強制保存が承諾された場合 */
  const handleOverrideConfirm = useCallback(() => {
    setShowOverrideDialog(false);
    void executeSave(true);
  }, [executeSave]);

  const prevMonth = useCallback(() => {
    if (month === 1) {
      onYearMonthChange(year - 1, 12);
    } else {
      onYearMonthChange(year, month - 1);
    }
  }, [month, year, onYearMonthChange]);

  const nextMonth = useCallback(() => {
    if (month === 12) {
      onYearMonthChange(year + 1, 1);
    } else {
      onYearMonthChange(year, month + 1);
    }
  }, [month, year, onYearMonthChange]);

  const hasDirtySlots = useMemo(() => {
    for (const dayState of Object.values(calendarState)) {
      for (const slotState of Object.values(dayState)) {
        if ((slotState as SlotState).isDirty) return true;
      }
    }
    return false;
  }, [calendarState]);

  // ドラッグ中のWorkerオブジェクト（DragOverlay用）
  const draggingWorker = useMemo(
    () => workers.find((w) => w.id === draggingWorkerId) ?? null,
    [workers, draggingWorkerId],
  );

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4">
        {/* カレンダーパネル */}
        <div className="flex-1 min-w-0">
          <SciFiPanel className="p-4">
            {/* ヘッダー：月ナビゲーション＆保存ボタン */}
            <div className="flex items-center justify-between mb-4">
              <SciFiButton variant="secondary" size="sm" onClick={prevMonth}>
                &lt;&lt; 前月
              </SciFiButton>
              <div className="flex items-center gap-2">
                <YearMonthPicker year={year} month={month} onChange={onYearMonthChange} />
                <span className="text-xs text-gray-400">{department.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <SciFiButton variant="secondary" size="sm" onClick={nextMonth}>
                  翌月 &gt;&gt;
                </SciFiButton>
                {!readOnly && (
                  <SciFiButton
                    variant="primary"
                    size="sm"
                    onClick={handleSave}
                    loading={isSaving}
                    disabled={!hasDirtySlots}
                  >
                    保存
                  </SciFiButton>
                )}
              </div>
            </div>

            {/* ローディング状態 */}
            {isLoading && (
              <div className="flex items-center justify-center py-12 text-gray-400 text-sm">
                <span className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
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
                      className={`text-center text-xs py-1 font-medium ${
                        i === 0
                          ? "text-red-500"
                          : i === 6
                            ? "text-blue-500"
                            : "text-gray-500"
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

                    // この日のスロットごとのバリデーション違反を収集する
                    const dayViolations: Partial<Record<SlotType, ValidationViolation[]>> = {};
                    for (const slotType of Object.keys(dayState) as SlotType[]) {
                      const key = buildSlotKey(dateStr, slotType);
                      const violations = validationMap[key];
                      if (violations && violations.length > 0) {
                        dayViolations[slotType] = violations;
                      }
                    }

                    return (
                      <CalendarCell
                        key={dateStr}
                        date={date}
                        dateStr={dateStr}
                        dayType={dayType}
                        isHoliday={holidayFlag}
                        holidayName={holidayName}
                        dayState={dayState}
                        workers={workers}
                        departments={departments}
                        skillRanks={skillRanks}
                        dayViolations={dayViolations}
                        isWorkerAvailable={isWorkerAvailable}
                        onWorkerChange={(slotType, idx2, wid) =>
                          handleWorkerChange(dateStr, slotType, idx2, wid)
                        }
                        onSlotFocus={handleSlotFocus}
                        readOnly={readOnly}
                      />
                    );
                  })}
                </div>

                {/* 凡例 */}
                <div className="mt-4 flex items-center gap-4 text-[10px] text-gray-500">
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-white border border-gray-200 inline-block" />
                    平日
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-blue-50 border border-blue-200 inline-block" />
                    土曜日
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-red-50 border border-red-200 inline-block" />
                    日曜・祝日
                  </span>
                  <span className="flex items-center gap-1">🎌 祝日</span>
                </div>
              </>
            )}
          </SciFiPanel>
        </div>

        {/* サイドパネル */}
        <div className="w-80 shrink-0">
          <div className="sticky top-4 h-[calc(100vh-8rem)]">
            <WorkerListPanel
              workers={workers}
              departments={departments}
              skillRanks={skillRanks}
              employmentTypes={employmentTypes}
              rules={rules.shift_rules}
              activeSlotType={activeSlot?.slotType ?? null}
              activeAssignedWorkerIds={activeAssignedWorkerIds}
              showAll={showAll}
              onShowAllChange={setShowAll}
              aggregateStats={aggregateStats}
              isAggregateStatsLoading={isAggregateStatsLoading}
              workerStats={workerStatsData?.items}
              annualLimits={annualLimits}
              calendarState={calendarState}
              currentDateStr={activeSlot?.dateStr}
              minIntervalDays={minIntervalDays}
              prevMonthDatesByWorker={prevMonthDatesByWorker}
            />
          </div>
        </div>
      </div>

      {/* ドラッグ中のWorkerCardオーバーレイ */}
      <DragOverlay>
        {draggingWorker && (
          <div className="opacity-90 rotate-2 scale-105">
            <WorkerCard
              worker={draggingWorker}
              departments={departments}
              skillRanks={skillRanks}
            />
          </div>
        )}
      </DragOverlay>

      {/* オーバーライド確認ダイアログ */}
      <OverrideConfirmDialog
        isOpen={showOverrideDialog}
        violations={validationMap}
        onCancel={handleOverrideCancel}
        onConfirm={handleOverrideConfirm}
      />
    </DndContext>
  );
}
