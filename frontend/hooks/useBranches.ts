// frontend/hooks/useBranches.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type { Branch, BranchCreate, BranchUpdate } from "@/types/branch";

const BRANCHES_PATH = "/api/branches/";

/** Branch一覧取得・CRUD 操作を提供するカスタムフック */
export function useBranches() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [BRANCHES_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<Branch[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<Branch[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** Branchを作成する */
  const createBranch = useCallback(
    async (payload: BranchCreate): Promise<Branch> => {
      const api = await getApiClient();
      const created = await api.post<Branch>(BRANCHES_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** Branchを更新する */
  const updateBranch = useCallback(
    async (id: string, payload: BranchUpdate): Promise<Branch> => {
      const api = await getApiClient();
      const updated = await api.put<Branch>(`/api/branches/${id}`, payload);
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** Branchを削除する */
  const deleteBranch = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/branches/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    branches: data ?? [],
    isLoading,
    isError: !!error,
    error,
    createBranch,
    updateBranch,
    deleteBranch,
  };
}
