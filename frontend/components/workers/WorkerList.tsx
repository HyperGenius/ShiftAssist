// frontend/components/workers/WorkerList.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useDepartments } from "@/hooks/useDepartments";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import { useWorkers } from "@/hooks/useWorkers";
import type { Worker, WorkerCreate } from "@/types/worker";
import { DeleteConfirmModal } from "./DeleteConfirmModal";
import { WorkerModal } from "./WorkerModal";

/** スケルトンローダー行 */
function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[...Array(5)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-700/60 rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

/** Worker テーブル行 */
function WorkerRow({
  worker,
  departmentName,
  skillRankName,
  onEdit,
  onDelete,
}: {
  worker: Worker;
  departmentName: string;
  skillRankName: string;
  onEdit: (w: Worker) => void;
  onDelete: (w: Worker) => void;
}) {
  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-800/40 transition-colors">
      <td className="px-4 py-3 text-slate-200 font-medium">{worker.name}</td>
      <td className="px-4 py-3 text-slate-300">
        {departmentName}
      </td>
      <td className="px-4 py-3">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
        >
          {skillRankName}
        </span>
      </td>
      <td className="px-4 py-3">
        {worker.is_special ? (
          <span className="inline-flex items-center gap-1 text-xs text-purple-300">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 inline-block" />
            特別
          </span>
        ) : (
          <span className="text-xs text-slate-500">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <SciFiButton
            variant="secondary"
            size="sm"
            onClick={() => onEdit(worker)}
          >
            編集
          </SciFiButton>
          <SciFiButton
            variant="danger"
            size="sm"
            onClick={() => onDelete(worker)}
          >
            削除
          </SciFiButton>
        </div>
      </td>
    </tr>
  );
}

/** Worker 一覧・CRUD 管理コンポーネント */
export function WorkerList() {
  const { workers, isLoading, isError, createWorker, updateWorker, deleteWorker } =
    useWorkers();
  const { departments } = useDepartments();
  const { skillRankNameById } = useSkillRanks();

  const departmentNameById = Object.fromEntries(
    departments.map((d) => [d.id, d.name]),
  );

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWorker, setEditingWorker] = useState<Worker | undefined>(
    undefined,
  );
  const [deletingWorker, setDeletingWorker] = useState<Worker | undefined>(
    undefined,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleCreate = () => {
    setEditingWorker(undefined);
    setIsModalOpen(true);
  };

  const handleEdit = (worker: Worker) => {
    setEditingWorker(worker);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingWorker(undefined);
  };

  const handleSubmit = async (data: WorkerCreate) => {
    setIsSubmitting(true);
    try {
      if (editingWorker) {
        await updateWorker(editingWorker.id, data);
        toast.success(`"${data.name}" を更新しました`);
      } else {
        await createWorker(data);
        toast.success(`"${data.name}" を作成しました`);
      }
      handleModalClose();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "エラーが発生しました";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingWorker) return;
    setIsDeleting(true);
    try {
      await deleteWorker(deletingWorker.id);
      toast.success(`"${deletingWorker.name}" を削除しました`);
      setDeletingWorker(undefined);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "削除中にエラーが発生しました";
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <SciFiPanel className="p-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between mb-6">
          <SciFiHeading level="h2">対応者（Worker）管理</SciFiHeading>
          <SciFiButton onClick={handleCreate}>＋ 新規追加</SciFiButton>
        </div>

        {/* エラー表示 */}
        {isError && (
          <div className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400 mb-4">
            データの取得中にエラーが発生しました。再度お試しください。
          </div>
        )}

        {/* テーブル */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-700/60">
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium">
                  氏名
                </th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium">
                  所属課
                </th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium">
                  スキルランク
                </th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium">
                  特別雇用
                </th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium text-right">
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : workers.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-12 text-center text-slate-500"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <svg
                        className="w-10 h-10 text-slate-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1}
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                        />
                      </svg>
                      <p className="text-sm">
                        対応者が登録されていません
                      </p>
                      <p className="text-xs">
                        「新規追加」ボタンから登録してください
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                workers.map((worker) => (
                  <WorkerRow
                    key={worker.id}
                    worker={worker}
                    departmentName={departmentNameById[worker.department_id] ?? worker.department_id}
                    skillRankName={skillRankNameById[worker.skill_rank_id] ?? worker.skill_rank_id}
                    onEdit={handleEdit}
                    onDelete={setDeletingWorker}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 件数表示 */}
        {!isLoading && workers.length > 0 && (
          <p className="mt-3 text-xs text-slate-500 text-right">
            {workers.length} 件
          </p>
        )}
      </SciFiPanel>

      {/* 作成・編集モーダル */}
      {isModalOpen && (
        <WorkerModal
          worker={editingWorker}
          onSubmit={handleSubmit}
          onCancel={handleModalClose}
          isSubmitting={isSubmitting}
        />
      )}

      {/* 削除確認モーダル */}
      {deletingWorker && (
        <DeleteConfirmModal
          worker={deletingWorker}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeletingWorker(undefined)}
          isDeleting={isDeleting}
        />
      )}
    </>
  );
}
