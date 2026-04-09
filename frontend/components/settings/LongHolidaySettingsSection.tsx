// frontend/components/settings/LongHolidaySettingsSection.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { SciFiSelect } from "@/components/ui/SciFiSelect";
import { useLongHolidayPeriods } from "@/hooks/useLongHolidayPeriods";
import type { LongHolidayPeriodCreate } from "@/types/longHolidayPeriod";

import { LongHolidayPeriodForm } from "./LongHolidayPeriodForm";
import { LongHolidayPeriodRow } from "./LongHolidayPeriodRow";

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => currentYear - 1 + i);

/** 長期休暇期間設定セクション */
export function LongHolidaySettingsSection() {
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);

  const {
    longHolidayPeriods,
    isLoading,
    createLongHolidayPeriod,
    updateLongHolidayPeriod,
    deleteLongHolidayPeriod,
  } = useLongHolidayPeriods(selectedYear);

  const handleCreate = async (payload: LongHolidayPeriodCreate) => {
    try {
      await createLongHolidayPeriod(payload);
      toast.success("長期休暇期間を登録しました");
    } catch {
      toast.error("登録に失敗しました");
    }
  };

  const handleUpdate = async (
    id: string,
    payload: { start_date?: string; end_date?: string },
  ) => {
    try {
      await updateLongHolidayPeriod(id, payload);
      toast.success("長期休暇期間を更新しました");
    } catch {
      toast.error("更新に失敗しました");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteLongHolidayPeriod(id);
      toast.success("長期休暇期間を削除しました");
    } catch {
      toast.error("削除に失敗しました");
    }
  };

  return (
    <div className="space-y-8">
      <SciFiPanel className="p-6 space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <h2 className="text-sm font-semibold tracking-widest text-gray-700 uppercase">
            長期休暇期間の設定
          </h2>
          <SciFiSelect
            id="lhp-year-filter"
            label="表示年"
            value={String(selectedYear)}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            className="w-32"
          >
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>
                {y}年
              </option>
            ))}
          </SciFiSelect>
        </div>

        {/* 登録済み一覧 */}
        <div className="space-y-2">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="h-12 rounded bg-gray-200 animate-pulse"
                />
              ))}
            </div>
          ) : longHolidayPeriods.length === 0 ? (
            <p className="text-sm text-gray-400">
              {selectedYear}年の長期休暇期間が登録されていません。
            </p>
          ) : (
            longHolidayPeriods.map((period) => (
              <LongHolidayPeriodRow
                key={period.id}
                period={period}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>

        {/* 新規追加フォーム */}
        <div className="border-t border-gray-100 pt-6">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
            新しい期間を追加
          </h3>
          <LongHolidayPeriodForm
            defaultYear={selectedYear}
            onSubmit={handleCreate}
          />
        </div>
      </SciFiPanel>
    </div>
  );
}
