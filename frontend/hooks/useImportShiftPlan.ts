"use client";

import { useAuth, useOrganization } from "@clerk/nextjs";
import { useCallback, useState } from "react";

import type { PlanStatus, ShiftPlanImportResponse } from "@/types/shiftPlan";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ImportShiftPlanParams = {
  file: File;
  planStatus?: PlanStatus;
  createdBy?: string;
};

export type UseImportShiftPlanResult = {
  importShiftPlan: (
    params: ImportShiftPlanParams,
  ) => Promise<ShiftPlanImportResponse>;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
};

/**
 * 過去シフトデータ一括インポートMutationフック。
 *
 * CSV/JSONファイルを指定してインポートAPIを呼び出す。
 * 対象年月はファイル内の date カラムから自動検出される。
 * 処理中はローディング状態を管理し、エラー時はエラーメッセージを返す。
 */
export function useImportShiftPlan(): UseImportShiftPlanResult {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setError(null);
  }, []);

  const importShiftPlan = useCallback(
    async (params: ImportShiftPlanParams): Promise<ShiftPlanImportResponse> => {
      if (!tenantId) {
        throw new Error("テナントIDが設定されていません。");
      }

      setIsLoading(true);
      setError(null);

      try {
        const token = await getToken();

        const formData = new FormData();
        formData.append("file", params.file);
        if (params.planStatus) {
          formData.append("plan_status", params.planStatus);
        }
        if (params.createdBy) {
          formData.append("created_by", params.createdBy);
        }

        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        headers["X-Tenant-Id"] = tenantId;

        const response = await fetch(
          `${API_BASE_URL}/api/shift-plans/import`,
          {
            method: "POST",
            headers,
            body: formData,
          },
        );

        if (!response.ok) {
          let message = `HTTP ${response.status}`;
          try {
            const body = (await response.json()) as { detail?: string };
            if (body.detail) {
              message =
                typeof body.detail === "string"
                  ? body.detail
                  : JSON.stringify(body.detail);
            }
          } catch {
            // ignore JSON parse error
          }
          const err = new Error(message);
          setError(message);
          throw err;
        }

        return (await response.json()) as ShiftPlanImportResponse;
      } finally {
        setIsLoading(false);
      }
    },
    [getToken, tenantId],
  );

  return { importShiftPlan, isLoading, error, reset };
}
