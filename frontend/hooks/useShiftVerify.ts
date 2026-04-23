// frontend/hooks/useShiftVerify.ts
// シフトプラン Before/After 集計差分を取得するカスタムフック
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

import { fetcher } from "@/utils/fetcher";
import type { ShiftVerifyResponse } from "@/types/workerStats";

type UseShiftVerifyOptions = {
  /** ShiftPlan Verify（インポートデータまたは currentPlanId）。存在する場合はこちらを優先する */
  shiftPlanId?: string | null;
  /** ShiftRequirement Verify（アプリ内作成シフト）。shiftPlanId がない場合に使用する */
  yearMonth?: string | null;
  /** フェッチを実行するか（ダイアログが開いているときのみ true にする） */
  enabled: boolean;
};

/**
 * シフトの Before/After 集計差分を取得するフック。
 *
 * - `shiftPlanId` がある場合: `/api/tenants/{tenantId}/shift-plans/{shiftPlanId}/verify`
 * - `yearMonth` のみの場合: `/api/tenants/{tenantId}/shift-requirements/verify?year_month={yearMonth}`
 */
export function useShiftVerify({ shiftPlanId, yearMonth, enabled }: UseShiftVerifyOptions) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const path = useMemo(() => {
    if (!tenantId || !enabled) return null;
    if (shiftPlanId) {
      return `/api/tenants/${tenantId}/shift-plans/${shiftPlanId}/verify`;
    }
    if (yearMonth) {
      return `/api/tenants/${tenantId}/shift-requirements/verify?year_month=${yearMonth}`;
    }
    return null;
  }, [tenantId, shiftPlanId, yearMonth, enabled]);

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
