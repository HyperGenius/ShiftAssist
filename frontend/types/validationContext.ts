// frontend/types/validationContext.ts
// シフトバリデーションコンテキストの TypeScript 型定義

import type { Worker } from "./worker";

export interface ValidationContextWorkerStats {
  worker_id: string;
  /** 当月の日曜・祝日昼間シフト回数 */
  sun_hol_day_this_month: number;
  /** 前年GWシフト参加回数 */
  gw_last_year: number;
  /** 前年年末年始シフト参加回数 */
  year_end_last_year: number;
  /** 直近のシフト日付（間隔チェック用）。未アサインの場合はnull */
  last_shift_date: string | null;
}

export interface ValidationContextResponse {
  workers: Worker[];
  worker_stats: ValidationContextWorkerStats[];
}
