"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { usePositions } from "@/hooks/usePositions";
import type { Position, PositionCreate } from "@/types/position";

/** 除外フラグのラベルマッピング */
const EXCLUSION_FLAG_LABELS: {
  key: keyof PositionCreate;
  label: string;
}[] = [
  { key: "is_excluded_from_gw", label: "GW除外" },
  { key: "is_excluded_from_sw", label: "SW除外" },
  { key: "is_excluded_from_year_end", label: "年末年始除外" },
  { key: "is_excluded_from_all_shifts", label: "全シフト除外" },
];

/** 新規役職追加フォーム */
function AddPositionForm({
  onAdd,
  isSubmitting,
}: {
  onAdd: (data: PositionCreate) => Promise<void>;
  isSubmitting: boolean;
}) {
  const [name, setName] = useState("");
  const [flags, setFlags] = useState({
    is_excluded_from_gw: false,
    is_excluded_from_sw: false,
    is_excluded_from_year_end: false,
    is_excluded_from_all_shifts: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onAdd({ name: name.trim(), ...flags });
    setName("");
    setFlags({
      is_excluded_from_gw: false,
      is_excluded_from_sw: false,
      is_excluded_from_year_end: false,
      is_excluded_from_all_shifts: false,
    });
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
      <SciFiInput
        id="new-position-name"
        label="役職名"
        placeholder="例: 係長、主任"
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={isSubmitting}
      />
      <div className="flex flex-wrap gap-4">
        {EXCLUSION_FLAG_LABELS.map(({ key, label }) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={flags[key as keyof typeof flags]}
              onChange={(e) =>
                setFlags((prev) => ({ ...prev, [key]: e.target.checked }))
              }
              disabled={isSubmitting}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
            />
            <span className="text-sm text-slate-300">{label}</span>
          </label>
        ))}
      </div>
      <SciFiButton type="submit" loading={isSubmitting} disabled={!name.trim()}>
        追加
      </SciFiButton>
    </form>
  );
}

/** 役職行コンポーネント */
function PositionRow({
  position,
  onUpdate,
  onDelete,
}: {
  position: Position;
  onUpdate: (id: string, data: Partial<PositionCreate>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(position.name);
  const [editFlags, setEditFlags] = useState({
    is_excluded_from_gw: position.is_excluded_from_gw,
    is_excluded_from_sw: position.is_excluded_from_sw,
    is_excluded_from_year_end: position.is_excluded_from_year_end,
    is_excluded_from_all_shifts: position.is_excluded_from_all_shifts,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSave = async () => {
    if (!editName.trim()) return;
    setIsSaving(true);
    try {
      await onUpdate(position.id, { name: editName.trim(), ...editFlags });
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(position.id);
    } finally {
      setIsDeleting(false);
    }
  };

  /** 有効な除外フラグのラベル一覧 */
  const activeFlags = EXCLUSION_FLAG_LABELS.filter(
    ({ key }) => position[key as keyof Position],
  ).map(({ label }) => label);

  if (isEditing) {
    return (
      <li className="py-3 border-b border-slate-700/40 space-y-3">
        <SciFiInput
          id={`edit-position-${position.id}`}
          label=""
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          disabled={isSaving}
        />
        <div className="flex flex-wrap gap-4">
          {EXCLUSION_FLAG_LABELS.map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={editFlags[key as keyof typeof editFlags]}
                onChange={(e) =>
                  setEditFlags((prev) => ({ ...prev, [key]: e.target.checked }))
                }
                disabled={isSaving}
                className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
              />
              <span className="text-sm text-slate-300">{label}</span>
            </label>
          ))}
        </div>
        <div className="flex gap-2">
          <SciFiButton size="sm" loading={isSaving} onClick={() => void handleSave()}>
            保存
          </SciFiButton>
          <SciFiButton
            size="sm"
            variant="ghost"
            disabled={isSaving}
            onClick={() => {
              setEditName(position.name);
              setEditFlags({
                is_excluded_from_gw: position.is_excluded_from_gw,
                is_excluded_from_sw: position.is_excluded_from_sw,
                is_excluded_from_year_end: position.is_excluded_from_year_end,
                is_excluded_from_all_shifts: position.is_excluded_from_all_shifts,
              });
              setIsEditing(false);
            }}
          >
            キャンセル
          </SciFiButton>
        </div>
      </li>
    );
  }

  return (
    <li className="flex items-center gap-3 py-2 border-b border-slate-700/40">
      <span className="flex-1 text-sm text-slate-200">{position.name}</span>
      <div className="flex flex-wrap gap-1">
        {activeFlags.map((label) => (
          <span
            key={label}
            className="text-xs text-cyan-400 border border-cyan-500/40 px-1.5 py-0.5 rounded"
          >
            {label}
          </span>
        ))}
      </div>
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

/** 役職マスタ設定フォームコンポーネント */
export function PositionSettingsForm() {
  const { positions, isLoading, isError, createPosition, updatePosition, deletePosition } =
    usePositions();
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async (data: PositionCreate) => {
    setIsAdding(true);
    try {
      await createPosition(data);
      toast.success(`"${data.name}" を追加しました`);
    } catch {
      toast.error("役職の追加に失敗しました");
    } finally {
      setIsAdding(false);
    }
  };

  const handleUpdate = async (id: string, data: Partial<PositionCreate>) => {
    try {
      await updatePosition(id, data);
      toast.success("役職を更新しました");
    } catch {
      toast.error("役職の更新に失敗しました");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePosition(id);
      toast.success("役職を削除しました");
    } catch (err: unknown) {
      const message =
        err instanceof Error && err.message.includes("400")
          ? "この役職はWorkerに紐づいているため削除できません。"
          : "役職の削除に失敗しました";
      toast.error(message);
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
        <SciFiHeading level="h3">役職一覧</SciFiHeading>
        <p className="text-xs text-slate-400">
          各除外フラグが有効な役職は、該当する長期休暇期間中のシフトアサインから除外されます。
        </p>

        {positions.length === 0 ? (
          <p className="text-sm text-slate-500 py-4 text-center">
            役職が登録されていません。以下から追加してください。
          </p>
        ) : (
          <ul className="space-y-0">
            {positions.map((position) => (
              <PositionRow
                key={position.id}
                position={position}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
              />
            ))}
          </ul>
        )}
      </SciFiPanel>

      <SciFiPanel className="p-6 space-y-4">
        <SciFiHeading level="h3">役職を追加</SciFiHeading>
        <AddPositionForm onAdd={handleAdd} isSubmitting={isAdding} />
      </SciFiPanel>
    </div>
  );
}
