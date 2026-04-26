"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type { ShiftPlanDetail } from "@/types/shiftPlan";

const SHIFT_PLANS_PATH = "/api/shift-plans/";

type UseShiftPlanOptions = {
  year: number;
  month: number;
};

type UseShiftPlanResult = {
  shiftPlan: ShiftPlanDetail | null;
  isLoading: boolean;
  error: unknown;
  /** 空のシフトプランを新規作成して SWR キャッシュを更新する */
  createShiftPlan: (createdBy: string) => Promise<ShiftPlanDetail>;
};

/** 指定年月のシフトプラン（過去インポートデータ）を取得するカスタムフック */
export function useShiftPlan({ year, month }: UseShiftPlanOptions): UseShiftPlanResult {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const yearMonth = `${year}-${String(month).padStart(2, "0")}`;

  const path = `${SHIFT_PLANS_PATH}?year_month=${yearMonth}`;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [path, null, tenantId] : null),
    [tenantId, path],
  );

  const { data, error, isLoading, mutate } = useSWR<ShiftPlanDetail | null>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ShiftPlanDetail | null>([p, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const createShiftPlan = useCallback(
    async (createdBy: string): Promise<ShiftPlanDetail> => {
      const token = await getToken();
      const api = createApiClient({ token, tenantId });
      const created = await api.post<ShiftPlanDetail>(SHIFT_PLANS_PATH, {
        target_year_month: yearMonth,
        created_by: createdBy,
      });
      await mutate(created, { revalidate: false });
      return created;
    },
    [getToken, tenantId, yearMonth, mutate],
  );

  return {
    shiftPlan: data ?? null,
    isLoading,
    error,
    createShiftPlan,
  };
}
