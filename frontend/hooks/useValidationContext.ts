"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/utils/fetcher";
import type { ValidationContextResponse } from "@/types/validationContext";

/**
 * シフト作成画面のバリデーションコンテキストを取得するカスタムフック。
 *
 * @param targetYearMonth - 対象年月（YYYY-MM形式）
 * @param startDate - 直近シフト日付の検索開始日（YYYY-MM-DD形式）。
 *   月跨ぎの勤務間隔チェックのため (月初日 - min_interval_days) を渡す。
 *   省略時は全期間が対象になる。
 */
export function useValidationContext(
  targetYearMonth: string | null,
  startDate?: string | null,
) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(() => {
    if (!tenantId || !targetYearMonth) return null;
    const params = new URLSearchParams({
      target_year_month: targetYearMonth,
    });
    if (startDate) {
      params.set("start_date", startDate);
    }
    return [`/api/shifts/validation-context?${params.toString()}`, null, tenantId];
  }, [tenantId, targetYearMonth, startDate]);

  const { data, error, isLoading } = useSWR<ValidationContextResponse>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ValidationContextResponse>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  return {
    validationContext: data ?? null,
    isLoading,
    isError: !!error,
    error,
  };
}
