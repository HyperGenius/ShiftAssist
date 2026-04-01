// frontend/components/departments/DepartmentModal.tsx
// 作成・編集フォームを表示するモーダルコンポーネント
"use client";

import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import type { Department, DepartmentCreate } from "@/types/department";
import { DepartmentForm } from "./DepartmentForm";

interface DepartmentModalProps {
  /** 編集対象 Department（新規作成時は undefined）*/
  department?: Department;
  onSubmit: (data: DepartmentCreate) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function DepartmentModal({
  department,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: DepartmentModalProps) {
  const title = department ? "部門を編集" : "部門を新規作成";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="department-modal-title"
    >
      <SciFiPanel className="w-full max-w-lg mx-4 p-6">
        <div className="flex flex-col gap-5">
          <SciFiHeading id="department-modal-title" level="h3">
            {title}
          </SciFiHeading>
          <DepartmentForm
            department={department}
            onSubmit={onSubmit}
            onCancel={onCancel}
            isSubmitting={isSubmitting}
          />
        </div>
      </SciFiPanel>
    </div>
  );
}
