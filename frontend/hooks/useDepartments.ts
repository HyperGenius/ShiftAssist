// frontend/hooks/useDepartments.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type { Department, DepartmentCreate, DepartmentListResponse, DepartmentUpdate } from "@/types/department";

const DEPARTMENTS_PATH = "/api/departments/";

/** Departments 一覧取得・CRUD 操作を提供するカスタムフック */
export function useDepartments() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [DEPARTMENTS_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<DepartmentListResponse>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<DepartmentListResponse>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** Department を作成する */
  const createDepartment = useCallback(
    async (payload: DepartmentCreate): Promise<Department> => {
      const api = await getApiClient();
      const created = await api.post<Department>(DEPARTMENTS_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** Department を更新する */
  const updateDepartment = useCallback(
    async (id: string, payload: DepartmentUpdate): Promise<Department> => {
      const api = await getApiClient();
      const updated = await api.put<Department>(`/api/departments/${id}`, payload);
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** Department を削除する */
  const deleteDepartment = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/departments/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    departments: data?.items ?? [],
    isLoading,
    isError: !!error,
    error,
    createDepartment,
    updateDepartment,
    deleteDepartment,
  };
}
