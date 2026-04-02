// frontend/types/shiftRules.ts
// シフトルール定義の TypeScript 型定義

/** シフト作成ルール設定 */
export interface ShiftRulesConfig {
  /** 最小勤務間隔（日数）。同一ワーカーの連続シフト間に必要な最低日数。 */
  min_interval_days: number;
  /** ペアに必須のスキルランク一覧。 */
  require_skill_ranks: string[];
  /** 同一所属課ペアを許可するか。 */
  allow_same_department: boolean;
  /** 特別雇用者が参加できるシフト種別一覧。 */
  special_employment_shifts: string[];
  /** 1スロットあたりの必要人数。 */
  workers_per_slot: number;
}

/** シフト警告設定 */
export interface ShiftWarningsConfig {
  /** 休日の連続アサインを警告するか。 */
  avoid_consecutive_holidays: boolean;
}

/** ルール定義APIレスポンス */
export interface ShiftRules {
  shift_rules: ShiftRulesConfig;
  warnings: ShiftWarningsConfig;
}

/** バックエンドからルールを取得できない場合に使用するデフォルト値 */
export const DEFAULT_SHIFT_RULES: ShiftRules = {
  shift_rules: {
    min_interval_days: 10,
    require_skill_ranks: ["rank_a"],
    allow_same_department: false,
    special_employment_shifts: ["weekday_night"],
    workers_per_slot: 2,
  },
  warnings: {
    avoid_consecutive_holidays: true,
  },
};
