"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useMemo } from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { createApiClient } from "@/utils/apiClient";
import { fetcher } from "@/utils/fetcher";
import type {
  ShiftRequirement,
  ShiftRequirementCreate,
  ShiftRequirementUpdate,
} from "@/types/shiftRequirement";

const SHIFT_REQUIREMENTS_PATH = "/api/shift-requirements/";

/** data が undefined のときに返す安定した参照（毎レンダーで新しい [] を作らないようにする） */
const EMPTY_REQUIREMENTS: ShiftRequirement[] = [];

/** ShiftRequirements 一覧取得・CRUD 操作を提供するカスタムフック */
export function useShiftRequirements() {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const swrKey = useMemo<[string, null, string | null] | null>(
    () => (tenantId ? [SHIFT_REQUIREMENTS_PATH, null, tenantId] : null),
    [tenantId],
  );

  const { data, error, isLoading } = useSWR<ShiftRequirement[]>(
    swrKey,
    async ([path, , tid]: [string, null, string | null]) => {
      const token = await getToken();
      return fetcher<ShiftRequirement[]>([path, token, tid]);
    },
    {
      revalidateOnFocus: false,
    },
  );

  const getApiClient = useCallback(async () => {
    const token = await getToken();
    return createApiClient({ token, tenantId });
  }, [getToken, tenantId]);

  /** ShiftRequirement を作成する */
  const createShiftRequirement = useCallback(
    async (payload: ShiftRequirementCreate): Promise<ShiftRequirement> => {
      const api = await getApiClient();
      const created = await api.post<ShiftRequirement>(
        SHIFT_REQUIREMENTS_PATH,
        payload,
      );
      await globalMutate(swrKey);
      return created;
    },
    [getApiClient, swrKey],
  );

  /** ShiftRequirement を更新する */
  const updateShiftRequirement = useCallback(
    async (
      id: string,
      payload: ShiftRequirementUpdate,
    ): Promise<ShiftRequirement> => {
      const api = await getApiClient();
      const updated = await api.put<ShiftRequirement>(
        `/api/shift-requirements/${id}`,
        payload,
      );
      await globalMutate(swrKey);
      return updated;
    },
    [getApiClient, swrKey],
  );

  /** ShiftRequirement を削除する */
  const deleteShiftRequirement = useCallback(
    async (id: string): Promise<void> => {
      const api = await getApiClient();
      await api.delete<undefined>(`/api/shift-requirements/${id}`);
      await globalMutate(swrKey);
    },
    [getApiClient, swrKey],
  );

  return {
    shiftRequirements: data ?? EMPTY_REQUIREMENTS,
    isLoading,
    isError: !!error,
    error,
    createShiftRequirement,
    updateShiftRequirement,
    deleteShiftRequirement,
  };
}
