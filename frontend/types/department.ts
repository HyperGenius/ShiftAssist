// frontend/types/department.ts
// Department エンティティの TypeScript 型定義

export interface Department {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  created_at: string;
  updated_at?: string;
  deleted_at: string | null;
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

export interface DepartmentBulkItem {
  name: string;
  code: string;
}

export interface DepartmentBulkRequest {
  departments: DepartmentBulkItem[];
}

export interface DepartmentBulkPreviewItem {
  code: string;
  name: string;
  action: "create" | "update" | "reactivate" | "no_change";
  old_name: string | null;
}

export interface DepartmentBulkPreviewResponse {
  preview: DepartmentBulkPreviewItem[];
  create_count: number;
  update_count: number;
  reactivate_count: number;
  no_change_count: number;
}

export interface DepartmentBulkUpsertResponse {
  created: number;
  updated: number;
  reactivated: number;
  items: Department[];
}

