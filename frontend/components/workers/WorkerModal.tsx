// frontend/components/workers/WorkerModal.tsx
// 作成・編集フォームを表示するモーダルコンポーネント
"use client";

import { Heading } from "@/components/ui/Heading";
import { Panel } from "@/components/ui/Panel";
import type { Worker, WorkerCreate } from "@/types/worker";
import { WorkerForm } from "./WorkerForm";

interface WorkerModalProps {
  /** 編集対象 Worker（新規作成時は undefined）*/
  worker?: Worker;
  onSubmit: (data: WorkerCreate) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function WorkerModal({
  worker,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: WorkerModalProps) {
  const title = worker ? "対応者を編集" : "対応者を新規作成";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="worker-modal-title"
    >
      <Panel className="w-full max-w-lg mx-4 p-6">
        <div className="flex flex-col gap-5">
          <Heading id="worker-modal-title" level="h3">
            {title}
          </Heading>
          <WorkerForm
            worker={worker}
            onSubmit={onSubmit}
            onCancel={onCancel}
            isSubmitting={isSubmitting}
          />
        </div>
      </Panel>
    </div>
  );
}
