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
}
