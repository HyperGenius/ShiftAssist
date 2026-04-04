// frontend/hooks/useLongHolidayPeriods.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  LongHolidayPeriod,
  LongHolidayPeriodCreate,
  LongHolidayPeriodUpdate,
} from "@/types/longHolidayPeriod";

const LONG_HOLIDAY_PERIODS_PATH = "/api/long-holiday-periods/";

/** LongHolidayPeriod一覧取得・CRUD 操作を提供するカスタムフック */
export function useLongHolidayPeriods(year?: number) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const path = year
    ? `${LONG_HOLIDAY_PERIODS_PATH}?year=${year}`
    : LONG_HOLIDAY_PERIODS_PATH;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [path, null, tenantId] : null),
    [tenantId, path],
  );

  const { data, error, isLoading } = useSWR<LongHolidayPeriod[]>(
    swrKey,
    async ([fetchPath, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<LongHolidayPeriod[]>([fetchPath, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** LongHolidayPeriodを作成する */
  const createLongHolidayPeriod = useCallback(
    async (payload: LongHolidayPeriodCreate): Promise<LongHolidayPeriod> => {
      const api = await getApiClient();
      const created = await api.post<LongHolidayPeriod>(
        LONG_HOLIDAY_PERIODS_PATH,
        payload,
      );
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** LongHolidayPeriodを更新する */
  const updateLongHolidayPeriod = useCallback(
    async (
      id: string,
      payload: LongHolidayPeriodUpdate,
    ): Promise<LongHolidayPeriod> => {
      const api = await getApiClient();
      const updated = await api.put<LongHolidayPeriod>(
        `/api/long-holiday-periods/${id}`,
        payload,
      );
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** LongHolidayPeriodを削除する */
  const deleteLongHolidayPeriod = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/long-holiday-periods/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    longHolidayPeriods: data ?? [],
    isLoading,
    isError: !!error,
    error,
    createLongHolidayPeriod,
    updateLongHolidayPeriod,
    deleteLongHolidayPeriod,
  };
}
