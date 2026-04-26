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
  forceOverwrite?: boolean;
};

export type ConflictInfo = {
  existingPlanId: string;
  targetYearMonth: string;
};

export type UseImportShiftPlanResult = {
  importShiftPlan: (
    params: ImportShiftPlanParams,
  ) => Promise<ShiftPlanImportResponse | null>;
  isLoading: boolean;
  error: string | null;
  conflictInfo: ConflictInfo | null;
  reset: () => void;
  resetConflict: () => void;
};

/**
 * 過去シフトデータ一括インポートMutationフック。
 *
 * CSV/JSONファイルを指定してインポートAPIを呼び出す。
 * 対象年月はファイル内の date カラムから自動検出される。
 * 処理中はローディング状態を管理し、エラー時はエラーメッセージを返す。
 * 同一年月のプランが存在する場合は conflictInfo に情報をセットする（409）。
 */
export function useImportShiftPlan(): UseImportShiftPlanResult {
  const { getToken } = useAuth();
  const { organization } = useOrganization();
  const tenantId = organization?.id ?? null;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictInfo, setConflictInfo] = useState<ConflictInfo | null>(null);

  const reset = useCallback(() => {
    setError(null);
    setConflictInfo(null);
  }, []);

  const resetConflict = useCallback(() => {
    setConflictInfo(null);
  }, []);

  const importShiftPlan = useCallback(
    async (
      params: ImportShiftPlanParams,
    ): Promise<ShiftPlanImportResponse | null> => {
      if (!tenantId) {
        throw new Error("テナントIDが設定されていません。");
      }

      setIsLoading(true);
      setError(null);
      setConflictInfo(null);

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
        if (params.forceOverwrite) {
          formData.append("force_overwrite", "true");
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
          if (response.status === 409) {
            try {
              const body = (await response.json()) as {
                detail?: {
                  existing_plan_id?: string;
                  target_year_month?: string;
                };
              };
              if (
                body.detail &&
                typeof body.detail === "object" &&
                body.detail.existing_plan_id &&
                body.detail.target_year_month
              ) {
                setConflictInfo({
                  existingPlanId: body.detail.existing_plan_id,
                  targetYearMonth: body.detail.target_year_month,
                });
                return null;
              }
            } catch {
              // JSON parse error は通常エラーとして処理
            }
          }

          let message = `HTTP ${response.status}`;
          try {
            const body = (await response.json()) as { detail?: unknown };
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

  return { importShiftPlan, isLoading, error, conflictInfo, reset, resetConflict };
}
