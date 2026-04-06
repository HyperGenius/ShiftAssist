"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  EmploymentType,
  EmploymentTypeCreate,
  EmploymentTypeUpdate,
} from "@/types/employmentType";

const EMPLOYMENT_TYPES_PATH = "/api/employment-types/";

/** 雇用形態一覧取得・CRUD 操作を提供するカスタムフック */
export function useEmploymentTypes() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [EMPLOYMENT_TYPES_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<EmploymentType[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<EmploymentType[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** 雇用形態を作成する */
  const createEmploymentType = useCallback(
    async (payload: EmploymentTypeCreate): Promise<EmploymentType> => {
      const api = await getApiClient();
      const created = await api.post<EmploymentType>(EMPLOYMENT_TYPES_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** 雇用形態を更新する */
  const updateEmploymentType = useCallback(
    async (id: string, payload: EmploymentTypeUpdate): Promise<EmploymentType> => {
      const api = await getApiClient();
      const updated = await api.put<EmploymentType>(
        `/api/employment-types/${id}`,
        payload,
      );
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** 雇用形態を削除する */
  const deleteEmploymentType = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/employment-types/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  /** IDから雇用形態名にマッピングするユーティリティ */
  const employmentTypeNameById = useMemo(
    () =>
      Object.fromEntries((data ?? []).map((et) => [et.id, et.name])),
    [data],
  );

  return {
    employmentTypes: data ?? [],
    isLoading,
    isError: !!error,
    error,
    employmentTypeNameById,
    createEmploymentType,
    updateEmploymentType,
    deleteEmploymentType,
  };
}
