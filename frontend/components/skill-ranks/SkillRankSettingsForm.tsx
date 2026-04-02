// frontend/components/skill-ranks/SkillRankSettingsForm.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import type { TenantSkillRank, TenantSkillRankCreate } from "@/types/skillRank";

/** 新規スキルランク追加フォーム */
function AddSkillRankForm({
  onAdd,
  isSubmitting,
}: {
  onAdd: (data: TenantSkillRankCreate) => Promise<void>;
  isSubmitting: boolean;
}) {
  const [name, setName] = useState("");
  const [isLeaderEligible, setIsLeaderEligible] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onAdd({ name: name.trim(), sort_order: 0, is_leader_eligible: isLeaderEligible });
    setName("");
    setIsLeaderEligible(false);
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex items-end gap-3">
      <div className="flex-1">
        <SciFiInput
          id="new-skill-rank-name"
          label="ランク名"
          placeholder="例: シニア、1級"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSubmitting}
        />
      </div>
      <div className="flex items-center gap-2 pb-0.5">
        <input
          id="new-is-leader-eligible"
          type="checkbox"
          checked={isLeaderEligible}
          onChange={(e) => setIsLeaderEligible(e.target.checked)}
          disabled={isSubmitting}
          className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
        />
        <label
          htmlFor="new-is-leader-eligible"
          className="text-sm text-slate-300 cursor-pointer whitespace-nowrap"
        >
          リーダー適性
        </label>
      </div>
      <SciFiButton type="submit" loading={isSubmitting} disabled={!name.trim()}>
        追加
      </SciFiButton>
    </form>
  );
}

/** スキルランク行コンポーネント */
function SkillRankRow({
  rank,
  onUpdate,
  onDelete,
}: {
  rank: TenantSkillRank;
  onUpdate: (id: string, name: string, isLeaderEligible: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(rank.name);
  const [editIsLeader, setEditIsLeader] = useState(rank.is_leader_eligible);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSave = async () => {
    if (!editName.trim()) return;
    setIsSaving(true);
    try {
      await onUpdate(rank.id, editName.trim(), editIsLeader);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(rank.id);
    } finally {
      setIsDeleting(false);
    }
  };

  if (isEditing) {
    return (
      <li className="flex items-center gap-3 py-2 border-b border-slate-700/40">
        <SciFiInput
          id={`edit-rank-${rank.id}`}
          label=""
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          disabled={isSaving}
          className="flex-1"
        />
        <div className="flex items-center gap-2">
          <input
            id={`edit-leader-${rank.id}`}
            type="checkbox"
            checked={editIsLeader}
            onChange={(e) => setEditIsLeader(e.target.checked)}
            disabled={isSaving}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
          />
          <label
            htmlFor={`edit-leader-${rank.id}`}
            className="text-sm text-slate-300 whitespace-nowrap"
          >
            リーダー適性
          </label>
        </div>
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
      <span className="flex-1 text-sm text-slate-200">{rank.name}</span>
      {rank.is_leader_eligible && (
        <span className="text-xs text-yellow-400 border border-yellow-500/40 px-1.5 py-0.5 rounded">
          リーダー適性
        </span>
      )}
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

/** スキルランク設定フォームコンポーネント */
export function SkillRankSettingsForm() {
  const { skillRanks, isLoading, isError, createSkillRank, updateSkillRank, deleteSkillRank } =
    useSkillRanks();
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async (data: TenantSkillRankCreate) => {
    setIsAdding(true);
    try {
      await createSkillRank({ ...data, sort_order: skillRanks.length });
      toast.success(`"${data.name}" を追加しました`);
    } catch {
      toast.error("スキルランクの追加に失敗しました");
    } finally {
      setIsAdding(false);
    }
  };

  const handleUpdate = async (id: string, name: string, isLeaderEligible: boolean) => {
    try {
      await updateSkillRank(id, { name, is_leader_eligible: isLeaderEligible });
      toast.success(`"${name}" を更新しました`);
    } catch {
      toast.error("スキルランクの更新に失敗しました");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteSkillRank(id);
      toast.success("スキルランクを削除しました");
    } catch {
      toast.error("スキルランクの削除に失敗しました");
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
        <SciFiHeading level="h3">スキルランク一覧</SciFiHeading>
        <p className="text-xs text-slate-400">
          リーダー適性（★印）を持つランクは、シフト編成時にペアに1名以上含める必要があります。
        </p>

        {skillRanks.length === 0 ? (
          <p className="text-sm text-slate-500 py-4 text-center">
            スキルランクが登録されていません。以下から追加してください。
          </p>
        ) : (
          <ul className="space-y-0">
            {skillRanks.map((rank) => (
              <SkillRankRow
                key={rank.id}
                rank={rank}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
              />
            ))}
          </ul>
        )}
      </SciFiPanel>

      <SciFiPanel className="p-6 space-y-4">
        <SciFiHeading level="h3">スキルランクを追加</SciFiHeading>
        <AddSkillRankForm onAdd={handleAdd} isSubmitting={isAdding} />
      </SciFiPanel>
    </div>
  );
}
