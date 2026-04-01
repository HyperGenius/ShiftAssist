export type SlotType =
  | "weekday_night"
  | "sat_day"
  | "sat_night"
  | "sun_hol_day"
  | "sun_hol_night"
  | "long_hol_day"
  | "long_hol_night";

export const SLOT_TYPE_LABELS: Record<SlotType, string> = {
  weekday_night: "夜間",
  sat_day: "昼間",
  sat_night: "夜間",
  sun_hol_day: "昼間",
  sun_hol_night: "夜間",
  long_hol_day: "昼間",
  long_hol_night: "夜間",
};

export interface ShiftRequirement {
  id: string;
  tenant_id: string;
  department_id: string;
  shift_date: string; // YYYY-MM-DD
  slot_type: SlotType;
  required_headcount: number;
  created_at: string;
  updated_at: string;
}

export interface ShiftRequirementCreate {
  department_id: string;
  shift_date: string;
  slot_type: SlotType;
  required_headcount: number;
}

export interface ShiftRequirementUpdate {
  required_headcount?: number;
}

/** カレンダー上の1スロット分のUIステート */
export interface SlotState {
  requirementId?: string; // 既存 ShiftRequirement の ID（更新時に使用）
  slot_type: SlotType;
  required_headcount: number;
  workerSelections: (string | null)[]; // ワーカーIDの配列（表示用・未保存）
  isDirty: boolean;
}

/** カレンダー上の1日分のUIステート（日付 → スロット配列） */
export type DayState = Record<string, SlotState>; // key: slot_type

/** カレンダー全体のUIステート（日付 → DayState） */
export type CalendarState = Record<string, DayState>; // key: YYYY-MM-DD
