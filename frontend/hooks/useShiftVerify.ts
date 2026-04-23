// frontend/hooks/useShiftVerify.ts
// シフトプラン Before/After 集計差分を取得するカスタムフック
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/utils/fetcher";
import type { ShiftVerifyResponse } from "@/types/workerStats";

/**
 * シフトプランの Before/After 集計差分を取得するフック。
 *
 * @param shiftPlanId - 検証対象のシフトプランID。null の場合はフェッチしない。
 */
export function useShiftVerify(shiftPlanId: string | null) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const path = useMemo(() => {
    if (!tenantId || !shiftPlanId) return null;
    return `/api/tenants/${tenantId}/shift-plans/${shiftPlanId}/verify`;
  }, [tenantId, shiftPlanId]);

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId && path ? [path, null, tenantId] : null),
    [tenantId, path],
  );

  const { data, error, isLoading } = useSWR<ShiftVerifyResponse>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ShiftVerifyResponse>([p, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  return {
    verifyData: data ?? null,
    isLoading,
    isError: !!error,
    error,
  };
}
