// frontend/types/department.ts
// Department エンティティの TypeScript 型定義

export interface Department {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  created_at: string;
  updated_at: string;
}

export interface DepartmentCreate {
  name: string;
  code: string;
}

export interface DepartmentUpdate {
  name?: string;
  code?: string;
}

export interface DepartmentListResponse {
  total: number;
  items: Department[];
}
