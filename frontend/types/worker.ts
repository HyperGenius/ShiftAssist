// frontend/types/worker.ts
// Worker エンティティの TypeScript 型定義

export interface Worker {
  id: string;
  tenant_id: string;
  name: string;
  department_id: string;
  skill_rank_id: string;
  is_special: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkerCreate {
  name: string;
  department_id: string;
  skill_rank_id: string;
  is_special: boolean;
}

export interface WorkerUpdate {
  name?: string;
  department_id?: string;
  skill_rank_id?: string;
  is_special?: boolean;
}

