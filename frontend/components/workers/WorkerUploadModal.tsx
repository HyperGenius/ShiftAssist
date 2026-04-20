// frontend/components/workers/WorkerUploadModal.tsx
// CSV/ExcelとJSONアップロードを統合したモーダルコンポーネント
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Heading } from "@/components/ui/Heading";
import { WorkerBulkUploadPanel } from "./WorkerBulkUploadPanel";
import { WorkerCsvUploadPanel } from "./WorkerCsvUploadPanel";

type UploadTab = "csv" | "json";

interface WorkerUploadModalProps {
  onClose: () => void;
}

/** 一括登録モーダル（CSV/Excel と JSON を切り替え） */
export function WorkerUploadModal({ onClose }: WorkerUploadModalProps) {
  const [activeTab, setActiveTab] = useState<UploadTab>("csv");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="一括登録"
    >
      {/* オーバーレイ */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* モーダル本体 */}
      <div className="relative z-10 w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-white rounded-lg shadow-xl">
        <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <Heading level="h2">一括登録</Heading>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="閉じる"
          >
            ✕
          </Button>
        </div>

        {/* タブ */}
        <div className="px-6 pt-4">
          <div className="flex gap-1 border-b border-gray-200">
            <button
              type="button"
              onClick={() => setActiveTab("csv")}
              className={[
                "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                activeTab === "csv"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
              ].join(" ")}
            >
              CSV/Excel
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("json")}
              className={[
                "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                activeTab === "json"
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
              ].join(" ")}
            >
              JSON
            </button>
          </div>
        </div>

        {/* パネル（Panelのラッパーを外してモーダル内に統合） */}
        <div className="p-6 pt-4">
          {activeTab === "csv" ? (
            <WorkerCsvUploadPanel onClose={onClose} />
          ) : (
            <WorkerBulkUploadPanel onClose={onClose} />
          )}
        </div>
      </div>
    </div>
  );
}
