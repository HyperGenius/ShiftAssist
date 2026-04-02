// frontend/hooks/useShiftRules.ts
// バックエンドからシフトルール定義を取得・キャッシュするカスタムフック
"use client";

import { useOrganization, useAuth } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/utils/fetcher";
import { DEFAULT_SHIFT_RULES, type ShiftRules } from "@/types/shiftRules";

const RULES_PATH = "/api/rules/";

/** バックエンドからシフトルール定義を取得するカスタムフック */
export function useShiftRules(): {
  rules: ShiftRules;
  isLoading: boolean;
  isError: boolean;
} {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [RULES_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<ShiftRules>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ShiftRules>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
      // ルール定義は頻繁に変わらないため、長めのキャッシュ期間を設定
      dedupingInterval: 60_000,
    },
  );

  return {
    rules: data ?? DEFAULT_SHIFT_RULES,
    isLoading,
    isError: !!error,
  };
}
