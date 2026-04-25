"use client";

import { Button } from "@/components/ui/Button";

interface UnsavedDataBannerProps {
  savedAt: string; // ISO 8601
  yearMonth: string; // YYYY-MM
  onRestore: () => void;
  onDiscard: () => void;
}

/** ページ遷移時の未保存データ警告バナーコンポーネント */
export function UnsavedDataBanner({ savedAt, yearMonth, onRestore, onDiscard }: UnsavedDataBannerProps) {
  const formatSavedAt = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString("ja-JP", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatYearMonth = (ym: string) => {
    const [year, month] = ym.split("-");
    return `${year}年${String(Number(month))}月`;
  };

  return (
    <div className="flex items-center justify-between gap-4 bg-yellow-50 border border-yellow-300 rounded-lg px-4 py-3 mb-3 text-sm">
      <span className="text-yellow-800">
        ⚠️ {formatYearMonth(yearMonth)}の下書きがあります（{formatSavedAt(savedAt)} に保存）。復元しますか？
      </span>
      <div className="flex gap-2 shrink-0">
        <Button variant="primary" size="sm" onClick={onRestore}>
          復元する
        </Button>
        <Button variant="secondary" size="sm" onClick={onDiscard}>
          破棄する
        </Button>
      </div>
    </div>
  );
}
