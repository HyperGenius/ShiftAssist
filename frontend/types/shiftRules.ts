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
  /** シフト対象とする部門コードの一覧。target_all_departments が false の場合に使用。 */
  target_departments: string[];
  /** テナント全体（全課）を対象とするか。true の場合は target_departments は無視される。 */
  target_all_departments: boolean;
  /** 採用（transfer_type=hired）のアサイン可能開始までの月数。0 で制限なし。 */
  hired_tenure_months: number;
  /** 事業部間転入（transfer_type=transfer_in かつ is_cross_division_transfer=true）のアサイン可能開始までの月数。0 で制限なし。 */
  cross_division_transfer_tenure_months: number;
}

/** 年間シフト回数上限設定 */
export interface AnnualShiftLimitsConfig {
  /** 全スロット合計の年間上限。0 で制限なし。 */
  annual_total: number;
  /** weekday_night の年間上限。0 で制限なし。 */
  weekday_night: number;
  /** sat_day の年間上限。0 で制限なし。 */
  sat_day: number;
  /** sat_night の年間上限。0 で制限なし。 */
  sat_night: number;
  /** sun_hol_day の年間上限（long_hol_day の実績を合算）。0 で制限なし。 */
  sun_hol_day: number;
  /** sun_hol_night の年間上限（long_hol_night の実績を合算）。0 で制限なし。 */
  sun_hol_night: number;
  /** sat_pre_hol_night の年間上限。0 で制限なし。 */
  sat_pre_hol_night: number;
}

/** シフト警告設定 */
export interface ShiftWarningsConfig {
  /** 休日の連続アサインを警告するか。 */
  avoid_consecutive_holidays: boolean;
  /** 年間シフト回数上限設定。 */
  annual_shift_limits: AnnualShiftLimitsConfig;
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
    target_departments: [],
    target_all_departments: true,
    hired_tenure_months: 6,
    cross_division_transfer_tenure_months: 3,
  },
  warnings: {
    avoid_consecutive_holidays: true,
    annual_shift_limits: {
      annual_total: 22,
      weekday_night: 10,
      sat_day: 3,
      sat_night: 3,
      sun_hol_day: 4,
      sun_hol_night: 5,
      sat_pre_hol_night: 4,
    },
  },
};
