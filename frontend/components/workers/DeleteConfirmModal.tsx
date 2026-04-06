// frontend/components/workers/DeleteConfirmModal.tsx
"use client";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import type { Worker } from "@/types/worker";

interface DeleteConfirmModalProps {
  worker: Worker;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
  isDeleting?: boolean;
}

export function DeleteConfirmModal({
  worker,
  onConfirm,
  onCancel,
  isDeleting = false,
}: DeleteConfirmModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-modal-title"
    >
      <SciFiPanel className="w-full max-w-sm mx-4 p-6">
        <div className="flex flex-col gap-4">
          {/* アイコン */}
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-500/20 border border-red-500/40 mx-auto">
            <svg
              className="w-6 h-6 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>

          <div className="text-center">
            <h2
              id="delete-modal-title"
              className="text-lg font-semibold text-gray-800 mb-1"
            >
              対応者を削除
            </h2>
            <p className="text-sm text-gray-500">
              <span className="text-gray-800 font-medium">
                &quot;{worker.name}&quot;
              </span>{" "}
              を削除しますか？
              <br />
              この操作は取り消せません。
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <SciFiButton
              type="button"
              variant="ghost"
              onClick={onCancel}
              disabled={isDeleting}
            >
              キャンセル
            </SciFiButton>
            <SciFiButton
              type="button"
              variant="danger"
              onClick={onConfirm}
              loading={isDeleting}
            >
              削除する
            </SciFiButton>
          </div>
        </div>
      </SciFiPanel>
    </div>
  );
}
