// frontend/components/departments/DepartmentList.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useDepartments } from "@/hooks/useDepartments";
import type { Department, DepartmentCreate } from "@/types/department";
import { ApiError } from "@/utils/apiClient";
import { DepartmentModal } from "./DepartmentModal";
import { DeleteDepartmentModal } from "./DeleteDepartmentModal";

/** スケルトンローダー行 */
function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[...Array(4)].map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-700/60 rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

/** Department テーブル行 */
function DepartmentRow({
  department,
  onEdit,
  onDelete,
}: {
  department: Department;
  onEdit: (d: Department) => void;
  onDelete: (d: Department) => void;
}) {
  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-800/40 transition-colors">
      <td className="px-4 py-3 text-slate-200 font-medium">{department.name}</td>
      <td className="px-4 py-3 text-slate-400 font-mono text-xs">
        {department.code}
      </td>
      <td className="px-4 py-3 text-slate-500 font-mono text-xs">
        {department.id.slice(0, 8)}…
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <SciFiButton
            variant="secondary"
            size="sm"
            onClick={() => onEdit(department)}
          >
            編集
          </SciFiButton>
          <SciFiButton
            variant="danger"
            size="sm"
            onClick={() => onDelete(department)}
          >
            削除
          </SciFiButton>
        </div>
      </td>
    </tr>
  );
}

/** Department 一覧・CRUD 管理コンポーネント */
export function DepartmentList() {
  const { departments, isLoading, isError, createDepartment, updateDepartment, deleteDepartment } =
    useDepartments();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState<Department | undefined>(
    undefined,
  );
  const [deletingDepartment, setDeletingDepartment] = useState<Department | undefined>(
    undefined,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleCreate = () => {
    setEditingDepartment(undefined);
    setIsModalOpen(true);
  };

  const handleEdit = (department: Department) => {
    setEditingDepartment(department);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingDepartment(undefined);
  };

  const handleSubmit = async (data: DepartmentCreate) => {
    setIsSubmitting(true);
    try {
      if (editingDepartment) {
        await updateDepartment(editingDepartment.id, data);
        toast.success(`"${data.name}" を更新しました`);
      } else {
        await createDepartment(data);
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
    if (!deletingDepartment) return;
    setIsDeleting(true);
    try {
      await deleteDepartment(deletingDepartment.id);
      toast.success(`"${deletingDepartment.name}" を削除しました`);
      setDeletingDepartment(undefined);
    } catch (err) {
      // バックエンドから 409 Conflict（所属スタッフがいる場合）のエラーをハンドリング
      const message =
        err instanceof ApiError && (err.status === 409 || err.status === 400)
          ? "この部門には所属しているスタッフがいるため削除できません"
          : err instanceof Error
            ? err.message
            : "削除中にエラーが発生しました";
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
          <SciFiHeading level="h2">部門（Department）管理</SciFiHeading>
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
                  部門名
                </th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium">
                  部門コード
                </th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider font-medium">
                  ID
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
              ) : departments.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
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
                          d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21"
                        />
                      </svg>
                      <p className="text-sm">
                        部門が登録されていません
                      </p>
                      <p className="text-xs">
                        「新規追加」ボタンから登録してください
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                departments.map((department) => (
                  <DepartmentRow
                    key={department.id}
                    department={department}
                    onEdit={handleEdit}
                    onDelete={setDeletingDepartment}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 件数表示 */}
        {!isLoading && departments.length > 0 && (
          <p className="mt-3 text-xs text-slate-500 text-right">
            {departments.length} 件
          </p>
        )}
      </SciFiPanel>

      {/* 作成・編集モーダル */}
      {isModalOpen && (
        <DepartmentModal
          department={editingDepartment}
          onSubmit={handleSubmit}
          onCancel={handleModalClose}
          isSubmitting={isSubmitting}
        />
      )}

      {/* 削除確認モーダル */}
      {deletingDepartment && (
        <DeleteDepartmentModal
          department={deletingDepartment}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeletingDepartment(undefined)}
          isDeleting={isDeleting}
        />
      )}
    </>
  );
}
