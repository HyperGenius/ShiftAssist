// frontend/hooks/useHolidays.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  TenantHoliday,
  TenantHolidayCreate,
} from "@/types/holiday";

const HOLIDAYS_PATH = "/api/holidays/";

function buildHolidaysPath(year?: number, month?: number): string {
  const params = new URLSearchParams();
  if (year !== undefined) params.set("year", String(year));
  if (month !== undefined) params.set("month", String(month));
  const qs = params.toString();
  return qs ? `${HOLIDAYS_PATH}?${qs}` : HOLIDAYS_PATH;
}

/** 休日一覧取得・CRUD 操作を提供するカスタムフック */
export function useHolidays(year?: number, month?: number) {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const path = buildHolidaysPath(year, month);

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [path, null, tenantId] : null),
    [tenantId, path],
  );

  const { data, error, isLoading } = useSWR<TenantHoliday[]>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<TenantHoliday[]>([p, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** 休日を1件または複数件追加する */
  const createHolidays = useCallback(
    async (holidays: TenantHolidayCreate[]): Promise<TenantHoliday[]> => {
      const api = await getApiClient();
      const created = await api.post<TenantHoliday[]>(HOLIDAYS_PATH, {
        holidays,
      });
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** 休日を削除する */
  const deleteHoliday = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/holidays/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    holidays: data ?? [],
    isLoading,
    isError: !!error,
    error,
    createHolidays,
    deleteHoliday,
  };
}
