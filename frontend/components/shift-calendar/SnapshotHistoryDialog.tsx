"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { ShiftPlanSnapshot } from "@/hooks/useShiftSnapshot";

interface SnapshotHistoryDialogProps {
  snapshots: ShiftPlanSnapshot[];
  onRestore: (snapshotId: string) => void;
  onClose: () => void;
}

/** スナップショット履歴・復元ダイアログコンポーネント */
export function SnapshotHistoryDialog({
  snapshots,
  onRestore,
  onClose,
}: SnapshotHistoryDialogProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleRestoreClick = () => {
    if (!selectedId) return;
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    if (!selectedId) return;
    onRestore(selectedId);
    setShowConfirm(false);
    onClose();
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        {!showConfirm ? (
          <>
            <h2 className="text-lg font-semibold mb-4">下書き履歴から復元</h2>
            {snapshots.length === 0 ? (
              <p className="text-sm text-gray-500 mb-4">下書き保存の履歴がありません。</p>
            ) : (
              <ul className="divide-y divide-gray-100 mb-4">
                {snapshots.map((snap) => (
                  <li
                    key={snap.id}
                    className={`flex items-center gap-3 py-3 px-2 cursor-pointer rounded transition-colors ${
                      selectedId === snap.id
                        ? "bg-blue-50 border border-blue-300"
                        : "hover:bg-gray-50"
                    }`}
                    onClick={() => setSelectedId(snap.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">
                        {formatDate(snap.created_at)}
                      </p>
                      <p className="text-xs text-gray-400 truncate">保存者: {snap.created_by}</p>
                    </div>
                    {selectedId === snap.id && (
                      <span className="text-blue-500 text-xs font-semibold">選択中</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={onClose}>
                キャンセル
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleRestoreClick}
                disabled={!selectedId}
              >
                復元する
              </Button>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-lg font-semibold mb-4">復元の確認</h2>
            <p className="text-sm text-gray-700 mb-6">
              選択した下書きを復元すると、現在のカレンダー状態が上書きされます。よろしいですか？
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setShowConfirm(false)}>
                戻る
              </Button>
              <Button variant="primary" size="sm" onClick={handleConfirm}>
                復元する
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
