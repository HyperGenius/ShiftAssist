"use client";
// frontend/hooks/useCustomRules.ts

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  CustomRule,
  CustomRuleCreate,
  CustomRuleUpdate,
} from "@/types/customRule";

const CUSTOM_RULES_PATH = "/api/custom-rules/";

/** カスタムルール一覧取得・CRUD 操作を提供するカスタムフック */
export function useCustomRules() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [CUSTOM_RULES_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<CustomRule[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<CustomRule[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** カスタムルールを作成する */
  const createCustomRule = useCallback(
    async (payload: CustomRuleCreate): Promise<CustomRule> => {
      const api = await getApiClient();
      const created = await api.post<CustomRule>(CUSTOM_RULES_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** カスタムルールを更新する */
  const updateCustomRule = useCallback(
    async (id: string, payload: CustomRuleUpdate): Promise<CustomRule> => {
      const api = await getApiClient();
      const updated = await api.put<CustomRule>(`/api/custom-rules/${id}`, payload);
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** カスタムルールを削除する */
  const deleteCustomRule = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/custom-rules/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  /** IDからカスタムルール名にマッピングするユーティリティ */
  const customRuleNameById = useMemo(
    () =>
      Object.fromEntries((data ?? []).map((r) => [r.id, r.name])),
    [data],
  );

  return {
    customRules: data ?? [],
    isLoading,
    isError: !!error,
    error,
    customRuleNameById,
    createCustomRule,
    updateCustomRule,
    deleteCustomRule,
  };
}
