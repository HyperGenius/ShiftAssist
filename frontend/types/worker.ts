// frontend/types/worker.ts
// Worker エンティティの TypeScript 型定義

export interface Worker {
  id: string;
  tenant_id: string;
  employee_no: string | null;
  name: string;
  department_id: string;
  skill_rank_id: string;
  is_special: boolean;
  joined_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkerCreate {
  employee_no?: string | null;
  name: string;
  department_id: string;
  skill_rank_id: string;
  is_special: boolean;
  joined_at?: string | null;
}

export interface WorkerUpdate {
  employee_no?: string | null;
  name?: string;
  department_id?: string;
  skill_rank_id?: string;
  is_special?: boolean;
  joined_at?: string | null;
}

export interface WorkerBulkItem {
  employee_no: string;
  name: string;
  department_code: string;
  department_name?: string | null;
  skill_rank_id: string;
  is_special: boolean;
  joined_at?: string | null;
}

export interface WorkerBulkRequest {
  workers: WorkerBulkItem[];
}

export interface WorkerBulkPreviewItem {
  employee_no: string;
  name: string;
  department_code: string;
  action: "create" | "update" | "no_change";
  old_name: string | null;
  department_is_new: boolean;
}

export interface WorkerBulkPreviewResponse {
  preview: WorkerBulkPreviewItem[];
  create_count: number;
  update_count: number;
  no_change_count: number;
  new_department_count: number;
}

export interface WorkerBulkUpsertResponse {
  created: number;
  updated: number;
  departments_created: number;
  items: Worker[];
}

