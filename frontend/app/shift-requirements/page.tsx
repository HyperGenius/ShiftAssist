"use client";

import { useState } from "react";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { ShiftCalendar } from "@/components/shift-calendar/ShiftCalendar";
import { useDepartments } from "@/hooks/useDepartments";
import type { Department } from "@/types/department";

export default function ShiftRequirementsPage() {
  const { departments, isLoading } = useDepartments();
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* ナビゲーションバー */}
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-sm font-semibold tracking-widest text-cyan-300 uppercase"
            >
              ShiftAssist
            </Link>
            <span className="text-slate-700">|</span>
            <span className="text-sm text-slate-400">シフト枠管理</span>
          </div>
          <UserButton />
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <SciFiHeading level="h1" className="mb-6">
          シフト枠カレンダー
        </SciFiHeading>

        {/* 部門選択 */}
        <SciFiPanel className="p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-xs text-slate-400 uppercase tracking-wider whitespace-nowrap">
              部門選択
            </label>
            {isLoading ? (
              <span className="text-xs text-slate-500">読み込み中...</span>
            ) : (
              <select
                value={selectedDept?.id ?? ""}
                onChange={(e) => {
                  const dept = departments.find((d) => d.id === e.target.value);
                  setSelectedDept(dept ?? null);
                }}
                className="bg-slate-800/60 border border-slate-600/50 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500/70 focus:border-cyan-500/70 transition-colors"
              >
                <option value="">-- 部門を選択してください --</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}（{d.code}）
                  </option>
                ))}
              </select>
            )}
          </div>
        </SciFiPanel>

        {/* カレンダー */}
        {selectedDept ? (
          <ShiftCalendar department={selectedDept} />
        ) : (
          <div className="flex items-center justify-center py-20 text-slate-500 text-sm">
            上の部門セレクトから部門を選択するとカレンダーが表示されます。
          </div>
        )}
      </main>
    </div>
  );
}
