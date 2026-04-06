// frontend/types/employmentType.ts
// EmploymentType エンティティの TypeScript 型定義

export interface EmploymentType {
  id: string;
  tenant_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface EmploymentTypeCreate {
  name: string;
}

export interface EmploymentTypeUpdate {
  name?: string;
}
