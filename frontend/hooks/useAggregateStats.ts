// frontend/hooks/useAggregateStats.ts
// ワーカーシフト集計情報を取得するカスタムフック
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/utils/fetcher";
import type { AggregateStatsResponse } from "@/types/workerStats";

/**
 * 選択年月を末月とした直近12ヶ月の集計情報を取得するフック。
 *
 * @param yearMonth - 集計末月（YYYY-MM形式）。省略時は当月。
 */
export function useAggregateStats(yearMonth?: string) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const path = useMemo(() => {
    if (!tenantId) return null;
    const base = `/api/tenants/${tenantId}/worker-stats/aggregate`;
    return yearMonth ? `${base}?year_month=${yearMonth}` : base;
  }, [tenantId, yearMonth]);

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId && path ? [path, null, tenantId] : null),
    [tenantId, path],
  );

  const { data, error, isLoading } = useSWR<AggregateStatsResponse>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<AggregateStatsResponse>([p, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  return {
    aggregateStats: data ?? null,
    isLoading,
    isError: !!error,
    error,
  };
}
