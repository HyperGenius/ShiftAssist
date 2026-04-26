// frontend/types/shiftPlan.ts
/** シフトプランのステータス */
export type PlanStatus = "draft" | "pending_approval" | "published";

/** 過去シフトデータインポート結果 */
export interface ShiftPlanImportResponse {
  plan_id: string;
  target_year_month: string;
  status: PlanStatus;
  slots_created: number;
  assignments_created: number;
  skipped_worker_ids: string[];
  overwritten: boolean;
}

/** シフトアサイン詳細（ShiftPlanDetail 内で使用） */
export interface ShiftAssignmentDetail {
  id: string;
  worker_id: string;
  is_manual_override: boolean;
}

/** シフトスロット詳細（ShiftPlanDetail 内で使用） */
export interface ShiftSlotDetail {
  id: string;
  /** ISO 8601 datetime 文字列 */
  date: string;
  slot_type: string;
  assignments: ShiftAssignmentDetail[];
}

/** シフトプラン詳細（スロット・アサイン情報を含む） */
export interface ShiftPlanDetail {
  id: string;
  title: string;
  target_year_month: string;
  status: PlanStatus;
  updated_at?: string | null;
  slots: ShiftSlotDetail[];
}
