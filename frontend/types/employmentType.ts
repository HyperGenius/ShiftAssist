// frontend/types/employmentType.ts
// EmploymentType エンティティの TypeScript 型定義

/** 年間シフト回数上限の部分的な上書き設定 */
export interface AnnualPartialLimitsConfig {
  /** 全スロット合計の年間上限の上書き値。null でグローバル設定に従う。0 で制限なし。 */
  annual_total?: number | null;
  /** weekday_night の年間上限の上書き値。 */
  weekday_night?: number | null;
  /** sat_day の年間上限の上書き値。 */
  sat_day?: number | null;
  /** sat_night の年間上限の上書き値。 */
  sat_night?: number | null;
  /** sun_hol_day の年間上限の上書き値。 */
  sun_hol_day?: number | null;
  /** sun_hol_night の年間上限の上書き値。 */
  sun_hol_night?: number | null;
  /** sat_pre_hol_night の年間上限の上書き値。 */
  sat_pre_hol_night?: number | null;
}

/** 雇用形態別シフトルール設定 */
export interface EmploymentTypeRuleConfig {
  /** True の場合、ペアにデフォルト雇用形態のWorkerが必須。 */
  require_default_pair: boolean;
  /** アサイン可能な SlotTypeEnum の一覧。null/空は制限なし（グローバル設定にフォールバック）。 */
  allowed_slot_types: string[] | null;
  /** 年間シフト回数上限の雇用形態ごとの上書き設定。 */
  annual_limit_overrides: AnnualPartialLimitsConfig | null;
}

export interface EmploymentType {
  id: string;
  tenant_id: string;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  rule?: EmploymentTypeRuleConfig | null;
}

export interface EmploymentTypeCreate {
  name: string;
  is_default?: boolean;
}

export interface EmploymentTypeUpdate {
  name?: string;
  is_default?: boolean;
}

export interface EmploymentTypeRuleUpdate {
  require_default_pair: boolean;
  allowed_slot_types: string[] | null;
  annual_limit_overrides: Record<string, number | null> | null;
}
