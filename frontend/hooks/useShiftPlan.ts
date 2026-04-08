"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useMemo } from "react";
import useSWR from "swr";

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

  const { data, error, isLoading } = useSWR<ShiftPlanDetail | null>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ShiftPlanDetail | null>([p, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  return {
    shiftPlan: data ?? null,
    isLoading,
    error,
  };
}
