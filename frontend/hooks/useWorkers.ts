// frontend/hooks/useWorkers.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  Worker,
  WorkerBulkPreviewResponse,
  WorkerBulkRequest,
  WorkerBulkUpsertResponse,
  WorkerCreate,
  WorkerUpdate,
  WorkerUploadPreviewResponse,
  WorkerUploadUpsertResponse,
} from "@/types/worker";

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

  /** バルクUpsertのプレビューを取得する */
  const previewBulkUpload = useCallback(
    async (payload: WorkerBulkRequest): Promise<WorkerBulkPreviewResponse> => {
      const api = await getApiClient();
      return api.post<WorkerBulkPreviewResponse>(
        "/api/workers/bulk/preview",
        payload,
      );
    },
    [getApiClient],
  );

  /** Worker を一括登録・更新する（Upsert） */
  const bulkUploadWorkers = useCallback(
    async (payload: WorkerBulkRequest): Promise<WorkerBulkUpsertResponse> => {
      const api = await getApiClient();
      const result = await api.post<WorkerBulkUpsertResponse>(
        "/api/workers/bulk",
        payload,
      );
      await globalMutate(swrKey);
      return result;
    },
    [getApiClient, swrKey],
  );

  /** CSV/Excelファイルをアップロードして差分プレビューを取得する（dry_run=true） */
  const previewUploadFile = useCallback(
    async (file: File): Promise<WorkerUploadPreviewResponse> => {
      const token = await getToken();
      const formData = new FormData();
      formData.append("file", file);

      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (tenantId) headers["X-Tenant-Id"] = tenantId;

      const res = await fetch(`/api/workers/upload?dry_run=true`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "アップロードのプレビューに失敗しました");
      }

      return res.json() as Promise<WorkerUploadPreviewResponse>;
    },
    [getToken, tenantId],
  );

  /** CSV/Excelファイルをアップロードして Upsert を実行する（dry_run=false） */
  const executeUploadFile = useCallback(
    async (file: File): Promise<WorkerUploadUpsertResponse> => {
      const token = await getToken();
      const formData = new FormData();
      formData.append("file", file);

      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (tenantId) headers["X-Tenant-Id"] = tenantId;

      const res = await fetch(`/api/workers/upload?dry_run=false`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "アップロードの実行に失敗しました");
      }

      const result = (await res.json()) as WorkerUploadUpsertResponse;
      await globalMutate(swrKey);
      return result;
    },
    [getToken, tenantId, swrKey],
  );

  return {
    workers: data ?? [],
    isLoading,
    isError: !!error,
    error,
    createWorker,
    updateWorker,
    deleteWorker,
    previewBulkUpload,
    bulkUploadWorkers,
    previewUploadFile,
    executeUploadFile,
  };
}
