// frontend/types/worker.ts
// Worker エンティティの TypeScript 型定義

export type TransferType = "no_transfer" | "transfer_in" | "transfer_out";

export interface Worker {
  id: string;
  tenant_id: string;
  employee_no: string | null;
  employee_code: string | null;
  name: string;
  department_id: string;
  skill_rank_id: string;
  position_id: string | null;
  employment_type_id: string | null;
  is_special: boolean;
  birth_date: string | null;
  skill_acquired_at: string | null;
  transfer_type: TransferType | null;
  transfer_scheduled_month: string | null;
  is_cross_division_transfer: boolean | null;
  joined_at: string | null;
  transferred_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkerCreate {
  employee_no?: string | null;
  employee_code?: string | null;
  name: string;
  department_id: string;
  skill_rank_id: string;
  position_id?: string | null;
  employment_type_id?: string | null;
  birth_date?: string | null;
  skill_acquired_at?: string | null;
  transfer_type?: TransferType | null;
  transfer_scheduled_month?: string | null;
  is_cross_division_transfer?: boolean | null;
  joined_at?: string | null;
  transferred_at?: string | null;
}

export interface WorkerUpdate {
  employee_no?: string | null;
  employee_code?: string | null;
  name?: string;
  department_id?: string;
  skill_rank_id?: string;
  position_id?: string | null;
  employment_type_id?: string | null;
  birth_date?: string | null;
  skill_acquired_at?: string | null;
  transfer_type?: TransferType | null;
  transfer_scheduled_month?: string | null;
  is_cross_division_transfer?: boolean | null;
  joined_at?: string | null;
  transferred_at?: string | null;
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

// --- CSV/Excel アップロード（職員番号ベース）---

export interface WorkerUploadRowValues {
  name: string | null;
  department_name: string | null;
  position_name: string | null;
  birth_date: string | null;
  skill_acquired_at: string | null;
  transfer_type: string | null;
  transfer_scheduled_month: string | null;
  is_cross_division_transfer: boolean | null;
}

export interface WorkerUploadDiffItem {
  row_index: number;
  employee_code: string;
  action: "create" | "update" | "no_change";
  before: WorkerUploadRowValues | null;
  after: WorkerUploadRowValues;
}

export interface WorkerUploadErrorRow {
  row_index: number;
  employee_code: string | null;
  errors: string[];
}

export interface WorkerUploadPreviewResponse {
  diff_items: WorkerUploadDiffItem[];
  error_rows: WorkerUploadErrorRow[];
  create_count: number;
  update_count: number;
  no_change_count: number;
  error_count: number;
  has_errors: boolean;
}

export interface WorkerUploadUpsertResponse {
  created: number;
  updated: number;
  items: Worker[];
}

