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
  position_name?: string | null;
  department_name?: string | null;
  skill_rank_name?: string | null;
  employment_type_name?: string | null;
  is_non_default_employment?: boolean;
  joined_at?: string | null; // YYYY-MM-DD
  skill_acquired_at?: string | null; // YYYY-MM-DD
}

/** 集計ページ用レスポンス型 */
export interface AggregateStatsResponse {
  year_month: string; // YYYY-MM
  period_months: number;
  items: AggregateWorkerStats[];
}

/** Verify機能用・weekday_night 枠の曜日別 Before/After 差分 */
export interface ShiftVerifyWeekdayDelta {
  weekday: 0 | 1 | 2 | 3; // 0=月, 1=火, 2=水, 3=木
  before_count: number;
  before_monthly_avg: number;
  after_count: number;
  after_monthly_avg: number;
  delta_count: number;
}

/** Verify機能用・枠種別ごとの Before/After 差分 */
export interface ShiftVerifySlotStat {
  slot_type: SlotType;
  before_count: number;
  before_monthly_avg: number;
  after_count: number;
  after_monthly_avg: number;
  delta_count: number;
  is_outlier: boolean;
  weekday_stats?: ShiftVerifyWeekdayDelta[];
}

/** Verify機能用・ワーカー1名分の統計 */
export interface ShiftVerifyWorkerItem {
  worker_id: string;
  worker_name: string;
  position_name?: string | null;
  department_name?: string | null;
  skill_rank_name?: string | null;
  employment_type_name?: string | null;
  is_non_default_employment: boolean;
  effective_months: number;
  slot_stats: ShiftVerifySlotStat[];
}

/** Verify機能用レスポンス型 */
export interface ShiftVerifyResponse {
  year_month: string; // YYYY-MM
  before_period: string; // e.g. "2025-06 〜 2026-05"
  after_period: string; // e.g. "2025-07 〜 2026-06"
  items: ShiftVerifyWorkerItem[];
}

/** 集計テーブル再計算結果レスポンス型 */
export interface RecalculateStatsResponse {
  year_month: string; // YYYY-MM
  upserted_months: string[];
}
