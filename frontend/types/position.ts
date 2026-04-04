// frontend/types/position.ts
// Position エンティティの TypeScript 型定義

export interface Position {
  id: string;
  tenant_id: string;
  name: string;
  is_excluded_from_gw: boolean;
  is_excluded_from_sw: boolean;
  is_excluded_from_year_end: boolean;
  is_excluded_from_all_shifts: boolean;
  created_at: string;
}

export interface PositionCreate {
  name: string;
  is_excluded_from_gw: boolean;
  is_excluded_from_sw: boolean;
  is_excluded_from_year_end: boolean;
  is_excluded_from_all_shifts: boolean;
}

export interface PositionUpdate {
  name?: string;
  is_excluded_from_gw?: boolean;
  is_excluded_from_sw?: boolean;
  is_excluded_from_year_end?: boolean;
  is_excluded_from_all_shifts?: boolean;
}
