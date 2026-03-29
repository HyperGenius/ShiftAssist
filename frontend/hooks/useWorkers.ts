// frontend/hooks/useWorkers.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type { Worker, WorkerCreate, WorkerUpdate } from "@/types/worker";

const WORKERS_PATH = "/api/workers/";

/** Workers 一覧取得・CRUD 操作を提供するカスタムフック */
export function useWorkers() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [WORKERS_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<Worker[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<Worker[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** Worker を作成する */
  const createWorker = useCallback(
    async (payload: WorkerCreate): Promise<Worker> => {
      const api = await getApiClient();
      const created = await api.post<Worker>(WORKERS_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** Worker を更新する */
  const updateWorker = useCallback(
    async (id: string, payload: WorkerUpdate): Promise<Worker> => {
      const api = await getApiClient();
      const updated = await api.put<Worker>(`/api/workers/${id}`, payload);
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** Worker を削除する */
  const deleteWorker = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/workers/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    workers: data ?? [],
    isLoading,
    isError: !!error,
    error,
    createWorker,
    updateWorker,
    deleteWorker,
  };
}
