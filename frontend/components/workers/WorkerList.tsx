// frontend/components/workers/WorkerList.tsx
"use client";

import { useMemo, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Heading } from "@/components/ui/Heading";
import { Panel } from "@/components/ui/Panel";
import { useDepartments } from "@/hooks/useDepartments";
import { useCustomRules } from "@/hooks/useCustomRules";
import { useEmploymentTypes } from "@/hooks/useEmploymentTypes";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import { useWorkers } from "@/hooks/useWorkers";
import type { Worker, WorkerCreate } from "@/types/worker";
import { matchesNormalized } from "@/utils/stringUtils";
import { DeleteConfirmModal } from "./DeleteConfirmModal";
import { WorkerModal } from "./WorkerModal";
import {
  INITIAL_FILTER_STATE,
  WorkerListFilter,
  isFilterActive,
  type WorkerFilterState,
} from "./WorkerListFilter";
import { WorkerUploadModal } from "./WorkerUploadModal";

/** スケルトンローダー行 */
function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[...Array(6)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
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
  employmentTypeName,
  customRuleName,
  onEdit,
  onDelete,
}: {
  worker: Worker;
  departmentName: string;
  skillRankName: string;
  employmentTypeName: string;
  customRuleName: string;
  onEdit: (w: Worker) => void;
  onDelete: (w: Worker) => void;
}) {
  return (
    <tr className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 text-gray-900 font-medium">{worker.name}</td>
      <td className="px-4 py-3 text-gray-600">
        {departmentName}
      </td>
      <td className="px-4 py-3">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
        >
          {skillRankName}
        </span>
      </td>
      <td className="px-4 py-3">
        {employmentTypeName ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            {employmentTypeName}
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        {customRuleName ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
            {customRuleName}
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(worker)}
            aria-label={`${worker.name} を編集`}
            className="p-1.5"
          >
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => onDelete(worker)}
            aria-label={`${worker.name} を削除`}
            className="p-1.5"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
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
  const { skillRanks, skillRankNameById } = useSkillRanks();
  const { employmentTypes, employmentTypeNameById } = useEmploymentTypes();
  const { customRuleNameById } = useCustomRules();

  const departmentNameById = useMemo(
    () => Object.fromEntries(departments.map((d) => [d.id, d.name])),
    [departments],
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
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  /** フィルタ状態 */
  const [filterState, setFilterState] = useState<WorkerFilterState>(INITIAL_FILTER_STATE);

  /** フィルタ適用済みのWorkerリスト */
  const filteredWorkers = useMemo(() => {
    return workers.filter((w) => {
      if (filterState.departmentId !== null && w.department_id !== filterState.departmentId) {
        return false;
      }
      if (filterState.skillRankId !== null && w.skill_rank_id !== filterState.skillRankId) {
        return false;
      }
      if (
        filterState.employmentTypeId !== null &&
        w.employment_type_id !== filterState.employmentTypeId
      ) {
        return false;
      }
      if (!matchesNormalized(w.name, filterState.nameQuery)) {
        return false;
      }
      return true;
    });
  }, [workers, filterState]);

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
      <Panel className="p-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between mb-6">
          <Heading level="h2">対応者（Worker）管理</Heading>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => setIsUploadModalOpen(true)}
            >
              一括登録
            </Button>
            <Button onClick={handleCreate}>＋ 新規追加</Button>
          </div>
        </div>

        {/* エラー表示 */}
        {isError && (
          <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-600 mb-4">
            データの取得中にエラーが発生しました。再度お試しください。
          </div>
        )}

        {/* フィルタ */}
        <WorkerListFilter
          departments={departments}
          skillRanks={skillRanks}
          employmentTypes={employmentTypes}
          filterState={filterState}
          onChange={setFilterState}
          onReset={() => setFilterState(INITIAL_FILTER_STATE)}
          filteredCount={filteredWorkers.length}
          totalCount={workers.length}
        />

        {/* テーブル */}
        <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-white z-10">
              <tr className="border-b border-gray-200">
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">
                  氏名
                </th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">
                  所属課
                </th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">
                  スキルランク
                </th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">
                  雇用形態
                </th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">
                  カスタムルール
                </th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">
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
              ) : filteredWorkers.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center text-gray-400"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <svg
                        className="w-10 h-10 text-gray-300"
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
                        {isFilterActive(filterState)
                          ? "条件に一致する対応者がいません"
                          : "対応者が登録されていません"}
                      </p>
                      <p className="text-xs">
                        {isFilterActive(filterState)
                          ? "フィルタ条件を変更してください"
                          : "「新規追加」ボタンから登録してください"}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredWorkers.map((worker) => (
                  <WorkerRow
                    key={worker.id}
                    worker={worker}
                    departmentName={departmentNameById[worker.department_id] ?? worker.department_id}
                    skillRankName={skillRankNameById[worker.skill_rank_id] ?? worker.skill_rank_id}
                    employmentTypeName={worker.employment_type_id ? (employmentTypeNameById[worker.employment_type_id] ?? "") : ""}
                    customRuleName={worker.custom_rule_id ? (customRuleNameById[worker.custom_rule_id] ?? "") : ""}
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
          <p className="mt-3 text-xs text-gray-400 text-right">
            {isFilterActive(filterState)
              ? `${filteredWorkers.length}/${workers.length} 件`
              : `${workers.length} 件`}
          </p>
        )}
      </Panel>

      {/* 一括登録モーダル */}
      {isUploadModalOpen && (
        <WorkerUploadModal onClose={() => setIsUploadModalOpen(false)} />
      )}

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
