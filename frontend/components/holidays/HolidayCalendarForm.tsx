// frontend/components/holidays/HolidayCalendarForm.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useHolidays } from "@/hooks/useHolidays";
import type { TenantHoliday, TenantHolidayCreate } from "@/types/holiday";

const CURRENT_YEAR = new Date().getFullYear();

/**
 * 祝日データ取得中に表示するローディング用スケルトンコンポーネント.
 *
 * バックエンドが初回アクセス時に内閣府データを元に祝日を自動投入するため、
 * その処理中であることをユーザーに示すメッセージを表示する。
 */
export function HolidayLoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 rounded border border-cyan-500/30 bg-cyan-500/10 px-4 py-3">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent flex-shrink-0" />
        <p className="text-sm text-cyan-300">内閣府ウェブサイトより祝日データ取得中</p>
      </div>
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 rounded bg-slate-800/60 animate-pulse" />
        ))}
      </div>
    </div>
  );
}

/** 新規休日追加フォーム */
function AddHolidayForm({
  onAdd,
  isSubmitting,
}: {
  onAdd: (data: TenantHolidayCreate) => Promise<void>;
  isSubmitting: boolean;
}) {
  const [holidayDate, setHolidayDate] = useState("");
  const [name, setName] = useState("");
  const [isLongHoliday, setIsLongHoliday] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!holidayDate || !name.trim()) return;
    await onAdd({ date: holidayDate, name: name.trim(), is_long_holiday: isLongHoliday });
    setHolidayDate("");
    setName("");
    setIsLongHoliday(false);
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
      <div className="flex items-end gap-3">
        <div className="w-44">
          <SciFiInput
            id="new-holiday-date"
            label="日付"
            type="date"
            value={holidayDate}
            onChange={(e) => setHolidayDate(e.target.value)}
            disabled={isSubmitting}
          />
        </div>
        <div className="flex-1">
          <SciFiInput
            id="new-holiday-name"
            label="名称"
            placeholder="例: 創立記念日"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isSubmitting}
          />
        </div>
        <div className="flex items-center gap-2 pb-0.5">
          <input
            id="new-is-long-holiday"
            type="checkbox"
            checked={isLongHoliday}
            onChange={(e) => setIsLongHoliday(e.target.checked)}
            disabled={isSubmitting}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
          />
          <label
            htmlFor="new-is-long-holiday"
            className="text-sm text-slate-300 cursor-pointer whitespace-nowrap"
          >
            長期連休
          </label>
        </div>
        <SciFiButton
          type="submit"
          loading={isSubmitting}
          disabled={!holidayDate || !name.trim()}
        >
          追加
        </SciFiButton>
      </div>
    </form>
  );
}

/** 休日行コンポーネント */
function HolidayRow({
  holiday,
  onDelete,
}: {
  holiday: TenantHoliday;
  onDelete: (id: string) => Promise<void>;
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(holiday.id);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <li className="flex items-center gap-3 py-2 border-b border-slate-700/40">
      <span className="w-32 text-sm text-slate-300 tabular-nums">{holiday.date}</span>
      <span className="flex-1 text-sm text-slate-200">{holiday.name}</span>
      {holiday.is_long_holiday && (
        <span className="text-xs text-amber-400 border border-amber-500/40 px-1.5 py-0.5 rounded">
          長期連休
        </span>
      )}
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

/**
 * 翌年祝日取得可能かを判定する.
 *
 * 内閣府が翌年の祝日を公開するのは例年9月頃であるため、
 * 実行月が9月（9）以降の場合のみ翌年データの取得を許可する。
 */
export function getMaxSelectableYear(
  currentYear: number = CURRENT_YEAR,
  currentMonth: number = new Date().getMonth() + 1,
): number {
  return currentMonth >= 9 ? currentYear + 1 : currentYear;
}

/** 年セレクター */
function YearSelector({
  year,
  maxYear,
  onChange,
}: {
  year: number;
  maxYear: number;
  onChange: (year: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <SciFiButton
        size="sm"
        variant="ghost"
        onClick={() => onChange(year - 1)}
      >
        ◀
      </SciFiButton>
      <span className="w-16 text-center text-sm font-semibold text-slate-200 tabular-nums">
        {year}年
      </span>
      <SciFiButton
        size="sm"
        variant="ghost"
        disabled={year >= maxYear}
        onClick={() => onChange(year + 1)}
        title={year >= maxYear ? "翌年の祝日は9月以降に取得できます" : undefined}
      >
        ▶
      </SciFiButton>
    </div>
  );
}

/** 休日カレンダー設定フォームコンポーネント */
export function HolidayCalendarForm() {
  const maxYear = getMaxSelectableYear();
  const [selectedYear, setSelectedYear] = useState(CURRENT_YEAR);
  const [isAdding, setIsAdding] = useState(false);

  const { holidays, isLoading, isError, createHolidays, deleteHoliday } =
    useHolidays(selectedYear);

  const handleAdd = async (data: TenantHolidayCreate) => {
    setIsAdding(true);
    try {
      await createHolidays([data]);
      toast.success(`"${data.name}" を追加しました`);
    } catch {
      toast.error("休日の追加に失敗しました");
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteHoliday(id);
      toast.success("休日を削除しました");
    } catch {
      toast.error("休日の削除に失敗しました");
    }
  };

  if (isLoading) {
    return <HolidayLoadingSkeleton />;
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
        <div className="flex items-center justify-between">
          <SciFiHeading level="h3">休日一覧</SciFiHeading>
          <YearSelector year={selectedYear} maxYear={maxYear} onChange={setSelectedYear} />
        </div>
        <p className="text-xs text-slate-400">
          対象年のデータが未登録の場合、日本の標準祝日が自動的に投入されます。
          {maxYear === CURRENT_YEAR && (
            <span className="ml-1 text-slate-500">（翌年の祝日取得は9月以降に利用可能）</span>
          )}
        </p>

        {holidays.length === 0 ? (
          <p className="text-sm text-slate-500 py-4 text-center">
            {selectedYear}年の休日が登録されていません。
          </p>
        ) : (
          <ul className="space-y-0">
            {holidays.map((holiday) => (
              <HolidayRow
                key={holiday.id}
                holiday={holiday}
                onDelete={handleDelete}
              />
            ))}
          </ul>
        )}
      </SciFiPanel>

      <SciFiPanel className="p-6 space-y-4">
        <SciFiHeading level="h3">休日を追加</SciFiHeading>
        <AddHolidayForm onAdd={handleAdd} isSubmitting={isAdding} />
      </SciFiPanel>
    </div>
  );
}

