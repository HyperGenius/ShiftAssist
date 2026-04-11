// frontend/hooks/useAggregateStats.ts
// ワーカーシフト集計情報を取得するカスタムフック
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo, useState } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
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

  const { data, error, isLoading, mutate } = useSWR<AggregateStatsResponse>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<AggregateStatsResponse>([p, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const [isRecalculating, setIsRecalculating] = useState(false);
  const [recalculateError, setRecalculateError] = useState<string | null>(null);

  /** 集計テーブルを手動再計算して最新データを再取得する */
  const recalculate = useCallback(async () => {
    if (!tenantId) return;
    setIsRecalculating(true);
    setRecalculateError(null);
    try {
      const token = await getToken();
      const api = createApiClient({ token, tenantId });
      const recalcPath = `/api/tenants/${tenantId}/worker-stats/aggregate/recalculate${yearMonth ? `?year_month=${yearMonth}` : ""}`;
      await api.post<unknown>(recalcPath, {});
      // 再計算成功後、集計データを再フェッチする
      await mutate();
      // 他の年月で開いているタブのキャッシュも無効化
      await globalMutate(
        (key: unknown) =>
          Array.isArray(key) &&
          typeof key[0] === "string" &&
          key[0].includes("worker-stats/aggregate"),
        undefined,
        { revalidate: true },
      );
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "再計算に失敗しました。";
      setRecalculateError(message);
    } finally {
      setIsRecalculating(false);
    }
  }, [tenantId, yearMonth, getToken, mutate]);

  return {
    aggregateStats: data ?? null,
    isLoading,
    isError: !!error,
    error,
    recalculate,
    isRecalculating,
    recalculateError,
  };
}
