"use client";

import { useCallback, useRef, useState } from "react";
import { mutate as globalMutate } from "swr";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { useImportShiftPlan } from "@/hooks/useImportShiftPlan";
import type { PlanStatus, ShiftPlanImportResponse } from "@/types/shiftPlan";

const PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  published: "確定済み（published）",
  pending_approval: "承認待ち（pending_approval）",
  draft: "下書き（draft）",
};

const ACCEPTED_FILE_TYPES = ".csv,.json";

type Props = {
  onClose: () => void;
  onSuccess?: (result: ShiftPlanImportResponse) => void;
};

/**
 * 過去シフトデータ一括インポートモーダルコンポーネント。
 *
 * CSV/JSONファイルのドラッグ＆ドロップおよびファイル選択に対応する。
 * 対象年月とプランステータスを指定してインポートを実行する。
 */
export function ImportShiftPlanModal({ onClose, onSuccess }: Props) {
  const { importShiftPlan, isLoading, error, reset } = useImportShiftPlan();

  const [file, setFile] = useState<File | null>(null);
  const [targetYearMonth, setTargetYearMonth] = useState("");
  const [planStatus, setPlanStatus] = useState<PlanStatus>("published");
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<ShiftPlanImportResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = useCallback(
    (selectedFile: File | null) => {
      setFile(selectedFile);
      reset();
      setResult(null);
    },
    [reset],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFileChange(e.target.files?.[0] ?? null);
    },
    [handleFileChange],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) handleFileChange(dropped);
    },
    [handleFileChange],
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!file || !targetYearMonth) return;

      try {
        const importResult = await importShiftPlan({
          file,
          targetYearMonth,
          planStatus,
        });
        setResult(importResult);
        // シフトプラン一覧を再フェッチ
        await globalMutate(
          (key) => typeof key === "string" && key.startsWith("/api/shift-plans"),
        );
        onSuccess?.(importResult);
      } catch {
        // エラーは useImportShiftPlan が state で管理
      }
    },
    [file, targetYearMonth, planStatus, importShiftPlan, onSuccess],
  );

  const isValidYearMonth = /^\d{4}-\d{2}$/.test(targetYearMonth);
  const canSubmit = !!file && isValidYearMonth && !isLoading;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="relative w-full max-w-lg rounded-lg bg-white shadow-xl">
        {/* ヘッダー */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            過去シフトのインポート
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="閉じる"
          >
            ✕
          </button>
        </div>

        {result ? (
          /* 成功結果表示 */
          <div className="px-6 py-5 space-y-4">
            <div className="rounded-md bg-green-50 border border-green-200 p-4 space-y-2">
              <p className="text-sm font-medium text-green-800">
                ✓ インポートが完了しました
              </p>
              <ul className="text-sm text-green-700 space-y-1 mt-2">
                <li>対象年月: {result.target_year_month}</li>
                <li>ステータス: {PLAN_STATUS_LABELS[result.status]}</li>
                <li>シフト枠（作成）: {result.slots_created} 件</li>
                <li>アサイン（作成）: {result.assignments_created} 件</li>
                {result.skipped_worker_ids.length > 0 && (
                  <li className="text-amber-700">
                    スキップされた社員番号（{result.skipped_worker_ids.length}
                    件）:{" "}
                    {result.skipped_worker_ids.join(", ")}
                  </li>
                )}
              </ul>
            </div>
            <div className="flex justify-end">
              <SciFiButton variant="secondary" onClick={onClose}>
                閉じる
              </SciFiButton>
            </div>
          </div>
        ) : (
          /* フォーム */
          <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
            {/* ファイル選択 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                ファイル（CSV / JSON）
                <span className="text-red-500 ml-0.5">*</span>
              </label>
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={[
                  "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 cursor-pointer transition-colors",
                  isDragging
                    ? "border-blue-400 bg-blue-50"
                    : "border-gray-300 hover:border-gray-400 bg-gray-50",
                ].join(" ")}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_FILE_TYPES}
                  onChange={handleInputChange}
                  className="hidden"
                />
                {file ? (
                  <span className="text-sm text-gray-700 font-medium">
                    📄 {file.name}
                  </span>
                ) : (
                  <>
                    <span className="text-2xl">📂</span>
                    <span className="text-sm text-gray-500">
                      ファイルをドラッグ＆ドロップ、またはクリックして選択
                    </span>
                    <span className="text-xs text-gray-400">
                      対応形式: CSV (.csv), JSON (.json)
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* 対象年月 */}
            <div>
              <label
                htmlFor="targetYearMonth"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                対象年月
                <span className="text-red-500 ml-0.5">*</span>
              </label>
              <input
                id="targetYearMonth"
                type="month"
                value={targetYearMonth}
                onChange={(e) => setTargetYearMonth(e.target.value)}
                className="block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>

            {/* プランステータス */}
            <div>
              <label
                htmlFor="planStatus"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                プランステータス
              </label>
              <select
                id="planStatus"
                value={planStatus}
                onChange={(e) => setPlanStatus(e.target.value as PlanStatus)}
                className="block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {(
                  Object.entries(PLAN_STATUS_LABELS) as [PlanStatus, string][]
                ).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* エラー表示 */}
            {error && (
              <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* フォーマット説明 */}
            <details className="text-xs text-gray-500">
              <summary className="cursor-pointer hover:text-gray-700 transition-colors">
                ファイルフォーマット例を表示
              </summary>
              <div className="mt-2 space-y-2">
                <div>
                  <p className="font-medium text-gray-600">CSV:</p>
                  <pre className="mt-1 rounded bg-gray-100 p-2 overflow-x-auto">
                    {`date,slot_type,worker_id_1,worker_id_2\n2026-01-01,weekday_night,1234567,1357926`}
                  </pre>
                </div>
                <div>
                  <p className="font-medium text-gray-600">JSON:</p>
                  <pre className="mt-1 rounded bg-gray-100 p-2 overflow-x-auto">
                    {`[{"date":"2026-01-01","slot_type":"weekday_night","worker_ids":["1234567","1357926"]}]`}
                  </pre>
                </div>
              </div>
            </details>

            {/* アクションボタン */}
            <div className="flex items-center justify-end gap-3 pt-1">
              <SciFiButton
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={isLoading}
              >
                キャンセル
              </SciFiButton>
              <SciFiButton
                type="submit"
                variant="primary"
                loading={isLoading}
                disabled={!canSubmit}
              >
                インポート実行
              </SciFiButton>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
