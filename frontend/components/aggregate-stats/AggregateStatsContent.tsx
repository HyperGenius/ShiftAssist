// frontend/components/aggregate-stats/AggregateStatsContent.tsx
// 集計ページのメインコンテンツ（年月セレクター + 集計テーブル）
"use client";

import { useState } from "react";

import { useAggregateStats } from "@/hooks/useAggregateStats";

import { AggregateStatsTable } from "./AggregateStatsTable";
import { YearMonthPicker } from "./YearMonthPicker";

function getCurrentYearMonth(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

export function AggregateStatsContent() {
  const [yearMonth, setYearMonth] = useState<string>(getCurrentYearMonth());
  const {
    aggregateStats,
    isLoading,
    isError,
    recalculate,
    isRecalculating,
    recalculateError,
  } = useAggregateStats(yearMonth);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900 tracking-wide">
          シフト集計
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          選択月を末月とした直近12ヶ月の枠種別シフト回数・月平均を表示します。
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label
            htmlFor="year-month-picker"
            className="text-sm font-medium text-gray-700"
          >
            集計末月:
          </label>
          <YearMonthPicker
            id="year-month-picker"
            value={yearMonth}
            onChange={setYearMonth}
          />
          {aggregateStats && (
            <span className="text-xs text-gray-500">
              集計期間: {aggregateStats.period_months}ヶ月
            </span>
          )}
        </div>

        {/* 手動再計算ボタン */}
        <button
          type="button"
          onClick={recalculate}
          disabled={isRecalculating}
          className="inline-flex items-center gap-1.5 rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          title="直近12ヶ月の集計データを再計算します（1分に1回まで）"
        >
          {isRecalculating ? (
            <>
              <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
              再計算中...
            </>
          ) : (
            <>🔄 再計算</>
          )}
        </button>
      </div>

      {recalculateError && (
        <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
          {recalculateError}
        </div>
      )}

      {isLoading && (
        <div className="text-center py-12 text-sm text-gray-500">
          読み込み中...
        </div>
      )}

      {isError && (
        <div className="text-center py-12 text-sm text-red-500">
          データの取得に失敗しました。
        </div>
      )}

      {!isLoading && !isError && aggregateStats && (
        <AggregateStatsTable data={aggregateStats} />
      )}

      {!isLoading && !isError && aggregateStats && aggregateStats.items.length === 0 && (
        <div className="text-center py-12 text-sm text-gray-500">
          対応者が登録されていません。
        </div>
      )}
    </div>
  );
}
