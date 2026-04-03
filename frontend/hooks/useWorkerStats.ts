// frontend/hooks/useWorkerStats.ts
// ワーカー勤務実績統計を取得するカスタムフック
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  TenantStatsConfig,
  TenantWorkerStatsResponse,
  WorkerStatsResponse,
} from "@/types/workerStats";

/** テナント全ワーカーの統計一括取得フック */
export function useWorkerStats() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const statsPath = tenantId
    ? `/api/tenants/${tenantId}/worker-stats`
    : null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId && statsPath ? [statsPath, null, tenantId] : null),
    [tenantId, statsPath],
  );

  const { data, error, isLoading } = useSWR<TenantWorkerStatsResponse>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<TenantWorkerStatsResponse>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  return {
    stats: data ?? null,
    isLoading,
    isError: !!error,
    error,
  };
}

/** 個別ワーカーの統計取得フック */
export function useWorkerStatsSingle(workerId: string | null) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const statsPath = workerId ? `/api/workers/${workerId}/stats` : null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId && statsPath ? [statsPath, null, tenantId] : null),
    [tenantId, statsPath],
  );

  const { data, error, isLoading } = useSWR<WorkerStatsResponse>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<WorkerStatsResponse>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  return {
    workerStats: data ?? null,
    isLoading,
    isError: !!error,
    error,
  };
}

/** テナント統計設定の取得・更新フック */
export function useStatsConfig() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const configPath = tenantId
    ? `/api/tenants/${tenantId}/stats-config`
    : null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId && configPath ? [configPath, null, tenantId] : null),
    [tenantId, configPath],
  );

  const { data, error, isLoading } = useSWR<TenantStatsConfig>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<TenantStatsConfig>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
      dedupingInterval: 60_000,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** 統計集計期間を更新する */
  const updateStatsPeriod = useCallback(
    async (statsPeriodMonths: number): Promise<TenantStatsConfig> => {
      const api = await getApiClient();
      const updated = await api.put<TenantStatsConfig>(configPath!, {
        stats_period_months: statsPeriodMonths,
      });
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, configPath, swrKey],
  );

  return {
    statsConfig: data ?? null,
    isLoading,
    isError: !!error,
    updateStatsPeriod,
  };
}
