// frontend/components/workers/WorkerList.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Heading } from "@/components/ui/Heading";
import { Panel } from "@/components/ui/Panel";
import { useDepartments } from "@/hooks/useDepartments";
import { useEmploymentTypes } from "@/hooks/useEmploymentTypes";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import { useWorkers } from "@/hooks/useWorkers";
import { useWorkerStats } from "@/hooks/useWorkerStats";
import type { Worker, WorkerCreate } from "@/types/worker";
import type { WorkerStatsResponse } from "@/types/workerStats";
import { DeleteConfirmModal } from "./DeleteConfirmModal";
import { WorkerBulkUploadPanel } from "./WorkerBulkUploadPanel";
import { WorkerCsvUploadPanel } from "./WorkerCsvUploadPanel";
import { WorkerModal } from "./WorkerModal";

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

/** 休日勤務の偏りを示すバッジ */
function HolidayStatsBadge({
  stats,
  allAvg,
}: {
  stats: WorkerStatsResponse | undefined;
  allAvg: number;
}) {
  if (!stats) {
    return <span className="text-xs text-gray-400">—</span>;
  }

  const avg = stats.holiday_slot_monthly_avg;
  const isHigh = allAvg > 0 && avg > allAvg * 1.3;
  const isLow = allAvg > 0 && avg < allAvg * 0.7;

  const label = avg.toFixed(2);

  if (isHigh) {
    return (
      <span
        title={`休日勤務月平均: ${label}回（テナント平均比 +30%超）`}
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200 cursor-help"
      >
        ⚠ {label}
      </span>
    );
  }

  if (isLow) {
    return (
      <span
        title={`休日勤務月平均: ${label}回（テナント平均比 -30%超）`}
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 cursor-help"
      >
        ↓ {label}
      </span>
    );
  }

  return (
    <span
      title={`休日勤務月平均: ${label}回`}
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200 cursor-help"
    >
      {label}
    </span>
  );
}

/** Worker テーブル行 */
function WorkerRow({
  worker,
  departmentName,
  skillRankName,
  employmentTypeName,
  workerStats,
  allAvg,
  onEdit,
  onDelete,
}: {
  worker: Worker;
  departmentName: string;
  skillRankName: string;
  employmentTypeName: string;
  workerStats: WorkerStatsResponse | undefined;
  allAvg: number;
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
        <HolidayStatsBadge stats={workerStats} allAvg={allAvg} />
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onEdit(worker)}
          >
            編集
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => onDelete(worker)}
          >
            削除
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
  const { skillRankNameById } = useSkillRanks();
  const { employmentTypeNameById } = useEmploymentTypes();
  const { stats } = useWorkerStats();

  const departmentNameById = Object.fromEntries(
    departments.map((d) => [d.id, d.name]),
  );

  // ワーカーIDからstatsへのマップ
  const statsById = Object.fromEntries(
    (stats?.items ?? []).map((s) => [s.worker_id, s]),
  );

  // テナント平均の休日勤務月平均
  const allAvg =
    stats && stats.items.length > 0
      ? stats.items.reduce((sum, s) => sum + s.holiday_slot_monthly_avg, 0) /
        stats.items.length
      : 0;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWorker, setEditingWorker] = useState<Worker | undefined>(
    undefined,
  );
  const [deletingWorker, setDeletingWorker] = useState<Worker | undefined>(
    undefined,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isBulkUploadOpen, setIsBulkUploadOpen] = useState(false);
  const [isCsvUploadOpen, setIsCsvUploadOpen] = useState(false);

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
              onClick={() => {
                setIsCsvUploadOpen((prev) => !prev);
                setIsBulkUploadOpen(false);
              }}
            >
              CSV/Excelアップロード
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setIsBulkUploadOpen((prev) => !prev);
                setIsCsvUploadOpen(false);
              }}
            >
              JSON一括登録
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

        {/* テーブル */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
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
                  休日勤務/月
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
              ) : workers.length === 0 ? (
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
                    employmentTypeName={worker.employment_type_id ? (employmentTypeNameById[worker.employment_type_id] ?? "") : ""}
                    workerStats={statsById[worker.id]}
                    allAvg={allAvg}
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
            {workers.length} 件
          </p>
        )}
      </Panel>

      {/* CSV/Excelアップロードパネル */}
      {isCsvUploadOpen && (
        <div className="mt-4">
          <WorkerCsvUploadPanel onClose={() => setIsCsvUploadOpen(false)} />
        </div>
      )}

      {/* JSON一括登録パネル */}
      {isBulkUploadOpen && (
        <div className="mt-4">
          <WorkerBulkUploadPanel onClose={() => setIsBulkUploadOpen(false)} />
        </div>
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
