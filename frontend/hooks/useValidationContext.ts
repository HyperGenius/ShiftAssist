"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/utils/fetcher";
import type { ValidationContextResponse } from "@/types/validationContext";

/** シフト作成画面のバリデーションコンテキストを取得するカスタムフック */
export function useValidationContext(targetYearMonth: string | null) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () =>
      tenantId && targetYearMonth
        ? [
            `/api/shifts/validation-context?target_year_month=${encodeURIComponent(targetYearMonth)}`,
            null,
            tenantId,
          ]
        : null,
    [tenantId, targetYearMonth],
  );

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
