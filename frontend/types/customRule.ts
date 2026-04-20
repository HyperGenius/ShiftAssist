// frontend/types/customRule.ts
// カスタムルールエンティティの TypeScript 型定義

export interface CustomRule {
  id: string;
  tenant_id: string;
  name: string;
  allowed_slot_types: string[] | null;
  annual_limit_overrides: Record<string, number | null> | null;
  created_at: string;
  updated_at: string;
}

export interface CustomRuleCreate {
  name: string;
  allowed_slot_types?: string[] | null;
  annual_limit_overrides?: Record<string, number | null> | null;
}

export interface CustomRuleUpdate {
  name?: string;
  allowed_slot_types?: string[] | null;
  annual_limit_overrides?: Record<string, number | null> | null;
}
