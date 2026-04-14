"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useState } from "react";

import { createApiClient } from "@/utils/apiClient";

export type UseDeleteShiftPlanResult = {
  deleteShiftPlan: (planId: string) => Promise<void>;
  isLoading: boolean;
};

/**
 * シフトプラン削除Mutationフック。
 *
 * 指定したプランIDの DELETE /api/shift-plans/{plan_id} を呼び出す。
 * テナントに属さないプランを指定した場合は 404 エラーになる。
 */
export function useDeleteShiftPlan(): UseDeleteShiftPlanResult {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const [isLoading, setIsLoading] = useState(false);

  const deleteShiftPlan = useCallback(
    async (planId: string): Promise<void> => {
      if (!tenantId) {
        throw new Error("テナントIDが設定されていません。");
      }

      setIsLoading(true);
      try {
        const token = await getToken();
        const client = createApiClient({ token, tenantId });
        await client.delete<void>(`/api/shift-plans/${planId}`);
      } finally {
        setIsLoading(false);
      }
    },
    [getToken, tenantId],
  );

  return { deleteShiftPlan, isLoading };
}
