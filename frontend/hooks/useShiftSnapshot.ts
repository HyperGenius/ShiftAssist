"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";

export interface ShiftPlanSnapshot {
  id: string;
  shift_plan_id: string;
  snapshot_data: Record<string, unknown>;
  created_by: string;
  created_at: string; // ISO 8601
}

interface UseShiftSnapshotOptions {
  planId: string | null;
}

interface UseShiftSnapshotResult {
  snapshots: ShiftPlanSnapshot[];
  isLoading: boolean;
  error: unknown;
  /** スナップショットを作成する */
  createSnapshot: (snapshotData: Record<string, unknown>, createdBy: string) => Promise<ShiftPlanSnapshot>;
  /** スナップショットのデータを返す（復元用） */
  getSnapshotData: (snapshotId: string) => ShiftPlanSnapshot | undefined;
  /** SWR キャッシュを再検証する */
  refresh: () => Promise<void>;
}

/** スナップショット一覧取得・作成を提供するカスタムフック */
export function useShiftSnapshot({ planId }: UseShiftSnapshotOptions): UseShiftSnapshotResult {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const path = planId ? `/api/shift-plans/${planId}/snapshots` : null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId && path ? [path, null, tenantId] : null),
    [tenantId, path],
  );

  const { data, error, isLoading, mutate } = useSWR<ShiftPlanSnapshot[]>(
    swrKey,
    async ([p, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ShiftPlanSnapshot[]>([p, token, tid]);
    },
    { revalidateOnFocus: false },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  const createSnapshot = useCallback(
    async (snapshotData: Record<string, unknown>, createdBy: string): Promise<ShiftPlanSnapshot> => {
      if (!planId) throw new Error("planId が未指定です。");
      const api = await getApiClient();
      const created = await api.post<ShiftPlanSnapshot>(
        `/api/shift-plans/${planId}/snapshots`,
        { snapshot_data: snapshotData, created_by: createdBy },
      );
      await mutate();
      return created;
    },
    [planId, getApiClient, mutate],
  );

  const getSnapshotData = useCallback(
    (snapshotId: string): ShiftPlanSnapshot | undefined => {
      return (data ?? []).find((s) => s.id === snapshotId);
    },
    [data],
  );

  const refresh = useCallback(async () => {
    await mutate();
  }, [mutate]);

  return {
    snapshots: data ?? [],
    isLoading,
    error,
    createSnapshot,
    getSnapshotData,
    refresh,
  };
}
