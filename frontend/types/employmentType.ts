// frontend/types/employmentType.ts
// EmploymentType エンティティの TypeScript 型定義

export interface EmploymentType {
  id: string;
  tenant_id: string;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmploymentTypeCreate {
  name: string;
  is_default?: boolean;
}

export interface EmploymentTypeUpdate {
  name?: string;
  is_default?: boolean;
}
