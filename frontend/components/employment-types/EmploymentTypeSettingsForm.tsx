// frontend/components/employment-types/EmploymentTypeSettingsForm.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useEmploymentTypes } from "@/hooks/useEmploymentTypes";
import type { EmploymentType, EmploymentTypeCreate } from "@/types/employmentType";

/** 新規雇用形態追加フォーム */
function AddEmploymentTypeForm({
  onAdd,
  isSubmitting,
}: {
  onAdd: (data: EmploymentTypeCreate) => Promise<void>;
  isSubmitting: boolean;
}) {
  const [name, setName] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onAdd({ name: name.trim() });
    setName("");
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex items-end gap-3">
      <div className="flex-1">
        <SciFiInput
          id="new-employment-type-name"
          label="雇用形態名"
          placeholder="例: 正職員、非常勤、特別雇用"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSubmitting}
        />
      </div>
      <SciFiButton type="submit" loading={isSubmitting} disabled={!name.trim()}>
        追加
      </SciFiButton>
    </form>
  );
}

/** 雇用形態行コンポーネント */
function EmploymentTypeRow({
  employmentType,
  onUpdate,
  onDelete,
}: {
  employmentType: EmploymentType;
  onUpdate: (id: string, name: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(employmentType.name);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSave = async () => {
    if (!editName.trim()) return;
    setIsSaving(true);
    try {
      await onUpdate(employmentType.id, editName.trim());
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(employmentType.id);
    } finally {
      setIsDeleting(false);
    }
  };

  if (isEditing) {
    return (
      <li className="flex items-center gap-3 py-2 border-b border-slate-700/40">
        <SciFiInput
          id={`edit-employment-type-${employmentType.id}`}
          label=""
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          disabled={isSaving}
          className="flex-1"
        />
        <SciFiButton size="sm" loading={isSaving} onClick={() => void handleSave()}>
          保存
        </SciFiButton>
        <SciFiButton
          size="sm"
          variant="ghost"
          disabled={isSaving}
          onClick={() => setIsEditing(false)}
        >
          キャンセル
        </SciFiButton>
      </li>
    );
  }

  return (
    <li className="flex items-center gap-3 py-2 border-b border-slate-700/40">
      <span className="flex-1 text-sm text-slate-200">{employmentType.name}</span>
      <SciFiButton
        size="sm"
        variant="secondary"
        onClick={() => setIsEditing(true)}
      >
        編集
      </SciFiButton>
      <SciFiButton
        size="sm"
        variant="danger"
        loading={isDeleting}
        onClick={() => void handleDelete()}
      >
        削除
      </SciFiButton>
    </li>
  );
}

/** 雇用形態設定フォームコンポーネント */
export function EmploymentTypeSettingsForm() {
  const { employmentTypes, isLoading, isError, createEmploymentType, updateEmploymentType, deleteEmploymentType } =
    useEmploymentTypes();
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async (data: EmploymentTypeCreate) => {
    setIsAdding(true);
    try {
      await createEmploymentType(data);
      toast.success(`"${data.name}" を追加しました`);
    } catch {
      toast.error("雇用形態の追加に失敗しました");
    } finally {
      setIsAdding(false);
    }
  };

  const handleUpdate = async (id: string, name: string) => {
    try {
      await updateEmploymentType(id, { name });
      toast.success(`"${name}" を更新しました`);
    } catch {
      toast.error("雇用形態の更新に失敗しました");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteEmploymentType(id);
      toast.success("雇用形態を削除しました");
    } catch {
      toast.error("雇用形態の削除に失敗しました");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-10 rounded bg-slate-800/60 animate-pulse" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400">
        データの取得中にエラーが発生しました。再度お試しください。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SciFiPanel className="p-6 space-y-4">
        <SciFiHeading level="h3">雇用形態一覧</SciFiHeading>
        <p className="text-xs text-slate-400">
          テナント固有の雇用形態を定義します。スタッフ登録・一覧画面に反映されます。
        </p>

        {employmentTypes.length === 0 ? (
          <p className="text-sm text-slate-500 py-4 text-center">
            雇用形態が登録されていません。以下から追加してください。
          </p>
        ) : (
          <ul className="space-y-0">
            {employmentTypes.map((et) => (
              <EmploymentTypeRow
                key={et.id}
                employmentType={et}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
              />
            ))}
          </ul>
        )}
      </SciFiPanel>

      <SciFiPanel className="p-6 space-y-4">
        <SciFiHeading level="h3">雇用形態を追加</SciFiHeading>
        <AddEmploymentTypeForm onAdd={handleAdd} isSubmitting={isAdding} />
      </SciFiPanel>
    </div>
  );
}
