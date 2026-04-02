// frontend/types/skillRank.ts
// TenantSkillRank エンティティの TypeScript 型定義

export interface TenantSkillRank {
  id: string;
  tenant_id: string;
  name: string;
  sort_order: number;
  is_leader_eligible: boolean;
  created_at: string;
}

export interface TenantSkillRankCreate {
  name: string;
  sort_order: number;
  is_leader_eligible: boolean;
}

export interface TenantSkillRankUpdate {
  name?: string;
  sort_order?: number;
  is_leader_eligible?: boolean;
}
