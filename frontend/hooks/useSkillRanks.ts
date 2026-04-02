// frontend/hooks/useSkillRanks.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  TenantSkillRank,
  TenantSkillRankCreate,
  TenantSkillRankUpdate,
} from "@/types/skillRank";

const SKILL_RANKS_PATH = "/api/skill-ranks/";

/** スキルランク一覧取得・CRUD 操作を提供するカスタムフック */
export function useSkillRanks() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [SKILL_RANKS_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<TenantSkillRank[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<TenantSkillRank[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** スキルランクを作成する */
  const createSkillRank = useCallback(
    async (payload: TenantSkillRankCreate): Promise<TenantSkillRank> => {
      const api = await getApiClient();
      const created = await api.post<TenantSkillRank>(SKILL_RANKS_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** スキルランクを更新する */
  const updateSkillRank = useCallback(
    async (id: string, payload: TenantSkillRankUpdate): Promise<TenantSkillRank> => {
      const api = await getApiClient();
      const updated = await api.put<TenantSkillRank>(
        `/api/skill-ranks/${id}`,
        payload,
      );
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** スキルランクを削除する */
  const deleteSkillRank = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/skill-ranks/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  /** IDからスキルランク名にマッピングするユーティリティ */
  const skillRankNameById = useMemo(
    () =>
      Object.fromEntries((data ?? []).map((r) => [r.id, r.name])),
    [data],
  );

  return {
    skillRanks: data ?? [],
    isLoading,
    isError: !!error,
    error,
    skillRankNameById,
    createSkillRank,
    updateSkillRank,
    deleteSkillRank,
  };
}
