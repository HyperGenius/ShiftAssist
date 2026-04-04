// frontend/types/longHolidayPeriod.ts
// LongHolidayPeriod エンティティの TypeScript 型定義

export type LongHolidayType = "gw" | "sw" | "year_end";

export interface LongHolidayPeriod {
  id: string;
  tenant_id: string;
  holiday_type: LongHolidayType;
  year: number;
  start_date: string;
  end_date: string;
  created_at: string;
  updated_at: string;
}

export interface LongHolidayPeriodCreate {
  holiday_type: LongHolidayType;
  year: number;
  start_date: string;
  end_date: string;
}

export interface LongHolidayPeriodUpdate {
  start_date?: string;
  end_date?: string;
}
