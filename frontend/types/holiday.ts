// frontend/types/holiday.ts
// TenantHoliday エンティティの TypeScript 型定義

export interface TenantHoliday {
  id: string;
  tenant_id: string;
  date: string; // ISO 8601 date string: "YYYY-MM-DD"
  name: string;
  is_long_holiday: boolean;
  created_at: string;
}

export interface TenantHolidayCreate {
  date: string; // ISO 8601 date string: "YYYY-MM-DD"
  name: string;
  is_long_holiday: boolean;
}

export interface TenantHolidayBulkCreate {
  holidays: TenantHolidayCreate[];
}
