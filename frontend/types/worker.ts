// frontend/types/worker.ts
// Worker エンティティの TypeScript 型定義

export type SkillRank = "rank_a" | "rank_b" | "rank_c" | "rank_d";

export const SKILL_RANK_LABELS: Record<SkillRank, string> = {
  rank_a: "ランク A",
  rank_b: "ランク B",
  rank_c: "ランク C",
  rank_d: "ランク D",
};

export interface Worker {
  id: string;
  tenant_id: string;
  name: string;
  department_id: string;
  skill_rank: SkillRank;
  is_special: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkerCreate {
  name: string;
  department_id: string;
  skill_rank: SkillRank;
  is_special: boolean;
}

export interface WorkerUpdate {
  name?: string;
  department_id?: string;
  skill_rank?: SkillRank;
  is_special?: boolean;
}
