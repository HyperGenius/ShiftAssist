// frontend/hooks/usePositions.ts
"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type { Position, PositionCreate, PositionUpdate } from "@/types/position";

const POSITIONS_PATH = "/api/positions/";

/** Position一覧取得・CRUD 操作を提供するカスタムフック */
export function usePositions() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [POSITIONS_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<Position[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<Position[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** Positionを作成する */
  const createPosition = useCallback(
    async (payload: PositionCreate): Promise<Position> => {
      const api = await getApiClient();
      const created = await api.post<Position>(POSITIONS_PATH, payload);
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** Positionを更新する */
  const updatePosition = useCallback(
    async (id: string, payload: PositionUpdate): Promise<Position> => {
      const api = await getApiClient();
      const updated = await api.put<Position>(`/api/positions/${id}`, payload);
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** Positionを削除する */
  const deletePosition = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/positions/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    positions: data ?? [],
    isLoading,
    isError: !!error,
    error,
    createPosition,
    updatePosition,
    deletePosition,
  };
}
