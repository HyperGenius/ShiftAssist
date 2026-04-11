// frontend/types/workerStats.ts
// ワーカー勤務実績統計の TypeScript 型定義

export type SlotType =
  | "weekday_night"
  | "sat_day"
  | "sat_night"
  | "sun_hol_day"
  | "sun_hol_night"
  | "long_hol_day"
  | "long_hol_night"
  | "sat_pre_hol_night";

/** 枠種別ごとの勤務実績 */
export interface WorkerSlotStats {
  slot_type: SlotType;
  count: number;
  monthly_avg: number;
}

/** 個別ワーカーの統計 */
export interface WorkerStatsResponse {
  worker_id: string;
  worker_name: string;
  effective_months: number;
  slot_stats: WorkerSlotStats[];
  holiday_slot_monthly_avg: number;
}

/** テナント全ワーカーの統計一括レスポンス */
export interface TenantWorkerStatsResponse {
  stats_period_months: number;
  items: WorkerStatsResponse[];
}

/** テナント統計設定 */
export interface TenantStatsConfig {
  tenant_id: string;
  stats_period_months: number;
}

/** weekday_night 枠の曜日別集計 */
export interface WeekdayNightStats {
  weekday: 0 | 1 | 2 | 3; // 0=月, 1=火, 2=水, 3=木
  count: number;
  monthly_avg: number;
}

/** 集計ページ用・枠種別ごとの合計・月平均 */
export interface AggregateWorkerSlotStats {
  slot_type: SlotType;
  count: number;
  monthly_avg: number;
  weekday_stats?: WeekdayNightStats[]; // weekday_night の場合のみ
}

/** 集計ページ用・ワーカー1名分の統計 */
export interface AggregateWorkerStats {
  worker_id: string;
  worker_name: string;
  effective_months: number;
  slot_stats: AggregateWorkerSlotStats[];
}

/** 集計ページ用レスポンス型 */
export interface AggregateStatsResponse {
  year_month: string; // YYYY-MM
  period_months: number;
  items: AggregateWorkerStats[];
}
