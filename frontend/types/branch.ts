// frontend/types/branch.ts
// Branch エンティティの TypeScript 型定義

export interface Branch {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  created_at: string;
}

export interface BranchCreate {
  name: string;
  code: string;
}

export interface BranchUpdate {
  name?: string;
  code?: string;
}
