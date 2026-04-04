"use client";

import { useMemo, useState } from "react";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { ShiftCalendar } from "@/components/shift-calendar/ShiftCalendar";
import { useDepartments } from "@/hooks/useDepartments";
import { useShiftRules } from "@/hooks/useShiftRules";
import type { Department } from "@/types/department";

export default function ShiftRequirementsPage() {
  const { departments, isLoading: deptsLoading } = useDepartments();
  const { rules, isLoading: rulesLoading } = useShiftRules();
  const [activeDeptId, setActiveDeptId] = useState<string | null>(null);

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
    <div className="min-h-screen bg-slate-950">
      {/* メインコンテンツ */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <SciFiHeading level="h1" className="mb-6">
          シフト枠カレンダー
        </SciFiHeading>

        {/* 部門タブナビゲーション */}
        {!isLoading && targetDepts.length > 1 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {targetDepts.map((dept) => (
              <button
                key={dept.id}
                onClick={() => setActiveDeptId(dept.id)}
                className={[
                  "px-4 py-1.5 rounded text-sm font-medium tracking-wide transition-colors",
                  dept.id === activeDept?.id
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/50"
                    : "bg-slate-800/60 text-slate-400 border border-slate-600/50 hover:text-slate-200 hover:bg-slate-700/60",
                ].join(" ")}
              >
                {dept.name}
              </button>
            ))}
          </div>
        )}

        {/* カレンダー */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-500 text-sm">
            読み込み中...
          </div>
        ) : activeDept ? (
          <ShiftCalendar department={activeDept} />
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500 text-sm gap-3">
            <p>シフト対象部門が設定されていません。</p>
            <Link
              href="/settings"
              className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors"
            >
              テナント設定画面で対象部門を設定する →
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
