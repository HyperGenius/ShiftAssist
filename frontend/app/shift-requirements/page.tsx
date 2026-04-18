"use client";

import { Suspense, useMemo, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { mutate as globalMutate } from "swr";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Heading } from "@/components/ui/Heading";
import { ImportShiftPlanModal } from "@/components/shift-import/ImportShiftPlanModal";
import { ShiftCalendar } from "@/components/shift-calendar/ShiftCalendar";
import { useDepartments } from "@/hooks/useDepartments";
import { useShiftRules } from "@/hooks/useShiftRules";
import { useShiftPlan } from "@/hooks/useShiftPlan";
import { useDeleteShiftPlan } from "@/hooks/useDeleteShiftPlan";
import type { Department } from "@/types/department";

type ViewMode = "past" | "edit";

/** URL クエリパラメータから年月を読み取り、カレンダーを表示する内部コンポーネント */
function ShiftRequirementsContent() {
  const today = new Date();
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL から year/month を取得。未指定なら当月をデフォルトとする
  const calYear = (() => {
    const v = Number(searchParams.get("year"));
    return v > 0 ? v : today.getFullYear();
  })();
  const calMonth = (() => {
    const v = Number(searchParams.get("month"));
    return v >= 1 && v <= 12 ? v : today.getMonth() + 1;
  })();

  const { departments, isLoading: deptsLoading } = useDepartments();
  const { rules, isLoading: rulesLoading } = useShiftRules();
  const [activeDeptId, setActiveDeptId] = useState<string | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);

  // 表示モード: null = 未選択（pastPlan の有無で自動決定）、それ以外はユーザーが手動選択済み
  const [viewMode, setViewMode] = useState<ViewMode | null>(null);

  const { shiftPlan, isLoading: planLoading } = useShiftPlan({ year: calYear, month: calMonth });
  const { deleteShiftPlan, isLoading: deleteLoading } = useDeleteShiftPlan();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  /** 年月変更：URL クエリパラメータを更新して状態を永続化する */
  const handleYearMonthChange = useCallback((y: number, m: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("year", String(y));
    params.set("month", String(m));
    router.replace(`?${params.toString()}`);
    // 月が変わったら表示モードをリセット（pastPlan の存在で自動判定させる）
    setViewMode(null);
  }, [router, searchParams]);

  /** 過去シフトプランを削除する */
  const handleDeletePlan = useCallback(async () => {
    if (!shiftPlan) return;
    try {
      await deleteShiftPlan(shiftPlan.id);
      await globalMutate(
        (key) =>
          Array.isArray(key) &&
          typeof key[0] === "string" &&
          key[0].startsWith("/api/shift-plans"),
      );
      setShowDeleteConfirm(false);
      setViewMode(null);
      toast.success(`シフトプラン（${shiftPlan.target_year_month}）を削除しました`);
    } catch (err) {
      console.error("シフトプランの削除に失敗しました", err);
      toast.error("シフトプランの削除に失敗しました");
    }
  }, [shiftPlan, deleteShiftPlan]);

  // 実際に使うモード: ユーザーが選択していれば従う、未選択なら pastPlan があれば "past"、なければ "edit"
  const effectiveMode: ViewMode = viewMode ?? (shiftPlan ? "past" : "edit");

  const isLoading = deptsLoading || rulesLoading;

  /** テナント設定に基づいてシフト対象部門を絞り込む */
  const targetDepts = useMemo<Department[]>(() => {
    if (rules.shift_rules.target_all_departments) return departments;
    return departments.filter((d) =>
      rules.shift_rules.target_departments.includes(d.code),
    );
  }, [departments, rules]);

  /**
   * 選択中の部門を返す。
   * activeDeptId が未設定または対象外の場合は先頭の部門をフォールバックとして使用する。
   */
  const activeDept = useMemo<Department | null>(() => {
    if (targetDepts.length === 0) return null;
    return targetDepts.find((d) => d.id === activeDeptId) ?? targetDepts[0];
  }, [targetDepts, activeDeptId]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* メインコンテンツ */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <Heading level="h1">シフト枠カレンダー</Heading>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowImportModal(true)}
          >
            📥 過去シフトのインポート
          </Button>
        </div>

        {/* 部門タブナビゲーション */}
        {!isLoading && targetDepts.length > 1 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {targetDepts.map((dept) => (
              <button
                key={dept.id}
                onClick={() => setActiveDeptId(dept.id)}
                className={[
                  "px-4 py-1.5 rounded text-sm font-medium transition-colors",
                  dept.id === activeDept?.id
                    ? "bg-gray-100 text-gray-800 border border-gray-300"
                    : "bg-white text-gray-500 border border-gray-200 hover:text-gray-700 hover:bg-gray-50",
                ].join(" ")}
              >
                {dept.name}
              </button>
            ))}
          </div>
        )}

        {/* 表示モード切り替えタブ（過去データが存在するときのみ表示） */}
        {!isLoading && !planLoading && shiftPlan && (
          <div className="flex items-center justify-between mb-4 border-b border-gray-200">
            <div className="flex gap-1">
              <button
                onClick={() => setViewMode("past")}
                className={[
                  "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                  effectiveMode === "past"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700",
                ].join(" ")}
              >
                📋 過去シフト（{shiftPlan.target_year_month}）
              </button>
              <button
                onClick={() => setViewMode("edit")}
                className={[
                  "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                  effectiveMode === "edit"
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700",
                ].join(" ")}
              >
                ✏️ シフト枠編集
              </button>
            </div>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
              className="mb-1"
            >
              シフト表削除
            </Button>
          </div>
        )}

        {/* カレンダー */}
        {isLoading || planLoading ? (
          <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
            読み込み中...
          </div>
        ) : activeDept ? (
          <ShiftCalendar
            department={activeDept}
            year={calYear}
            month={calMonth}
            pastPlan={effectiveMode === "past" ? shiftPlan : null}
            readOnly={effectiveMode === "past"}
            onYearMonthChange={handleYearMonthChange}
          />
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-gray-400 text-sm gap-3">
            <p>シフト対象部門が設定されていません。</p>
            <Link
              href="/settings"
              className="text-blue-500 hover:text-blue-600 underline underline-offset-2 transition-colors"
            >
              テナント設定画面で対象部門を設定する →
            </Link>
          </div>
        )}
      </main>

      {/* 過去シフトインポートモーダル */}
      {showImportModal && (
        <ImportShiftPlanModal
          onClose={() => setShowImportModal(false)}
          onSuccess={() => setShowImportModal(false)}
        />
      )}

      {/* 削除確認ダイアログ */}
      {showDeleteConfirm && shiftPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="relative w-full max-w-sm rounded-lg bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h2 className="text-base font-semibold text-gray-900">
                過去シフトの削除
              </h2>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="閉じる"
              >
                ✕
              </button>
            </div>
            <div className="px-6 py-5 space-y-4">
              <p className="text-sm text-gray-700">
                <strong>{shiftPlan.target_year_month}</strong>{" "}
                の過去シフトプランを削除します。
                <br />
                紐づくシフト枠・アサイン情報もすべて削除されます。この操作は取り消せません。
              </p>
              <div className="flex items-center justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleteLoading}
                >
                  キャンセル
                </Button>
                <Button
                  variant="danger"
                  onClick={handleDeletePlan}
                  loading={deleteLoading}
                  disabled={deleteLoading}
                >
                  削除する
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** useSearchParams を使用するためのフォールバック付きラッパー */
export default function ShiftRequirementsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-20 text-gray-400 text-sm">
          読み込み中...
        </div>
      }
    >
      <ShiftRequirementsContent />
    </Suspense>
  );
}
