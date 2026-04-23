// frontend/components/shift-calendar/ShiftVerifyDialog.tsx
// シフト Verify ダイアログコンポーネント（Before/After 集計差分表示）
"use client";

import { ShiftVerifyTable } from "./ShiftVerifyTable";
import { useShiftVerify } from "@/hooks/useShiftVerify";

interface ShiftVerifyDialogProps {
  /** ダイアログを表示するか */
  isOpen: boolean;
  /** 検証対象のシフトプランID */
  shiftPlanId: string;
  /** シフトプランの対象年月（YYYY-MM） */
  yearMonth: string;
  /** 閉じる時のコールバック */
  onClose: () => void;
}

/** シフト Verify ダイアログ — Verify ボタン押下時に開くモーダル */
export function ShiftVerifyDialog({
  isOpen,
  shiftPlanId,
  yearMonth,
  onClose,
}: ShiftVerifyDialogProps) {
  const { verifyData, isLoading, isError } = useShiftVerify(isOpen ? shiftPlanId : null);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="relative w-full max-w-[95vw] max-h-[90vh] rounded-lg bg-white shadow-xl flex flex-col">
        {/* ヘッダー */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-gray-900">
              シフト Verify — {yearMonth}
            </h2>
            {verifyData && (
              <p className="text-xs text-gray-500 mt-0.5">
                Before: {verifyData.before_period}　After: {verifyData.after_period}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors ml-4"
            aria-label="閉じる"
          >
            ✕
          </button>
        </div>

        {/* コンテンツ */}
        <div className="flex-1 overflow-auto px-6 py-4">
          {isLoading && (
            <div className="flex items-center justify-center py-12 text-gray-400 text-sm">
              <span className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />
              集計データを読み込み中...
            </div>
          )}

          {isError && !isLoading && (
            <div className="flex items-center justify-center py-12 text-red-500 text-sm">
              集計データの取得に失敗しました。
            </div>
          )}

          {verifyData && !isLoading && <ShiftVerifyTable data={verifyData} />}
        </div>

        {/* フッター */}
        <div className="flex justify-end border-t border-gray-200 px-6 py-3 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}
