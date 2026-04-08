"use client";

interface YearMonthPickerProps {
  year: number;
  month: number;
  onChange: (year: number, month: number) => void;
  /** 表示する年の範囲（デフォルト: 現在年-1 〜 現在年+2） */
  yearRange?: { min: number; max: number };
}

const MONTH_LABELS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

/** 年・月を直接選択できるコンパクトなピッカーコンポーネント */
export function YearMonthPicker({ year, month, onChange, yearRange }: YearMonthPickerProps) {
  const currentYear = new Date().getFullYear();
  const min = yearRange?.min ?? currentYear - 1;
  const max = yearRange?.max ?? currentYear + 2;

  const years: number[] = [];
  for (let y = min; y <= max; y++) {
    years.push(y);
  }

  const selectClass =
    "bg-white border border-gray-300 rounded px-2 py-1 text-sm font-semibold text-gray-800 " +
    "focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors duration-150 cursor-pointer";

  return (
    <div className="flex items-center gap-1">
      <select
        value={year}
        onChange={(e) => onChange(Number(e.target.value), month)}
        className={selectClass}
        aria-label="年を選択"
      >
        {years.map((y) => (
          <option key={y} value={y}>
            {y}年
          </option>
        ))}
      </select>
      <select
        value={month}
        onChange={(e) => onChange(year, Number(e.target.value))}
        className={selectClass}
        aria-label="月を選択"
      >
        {MONTH_LABELS.map((label, i) => (
          <option key={i + 1} value={i + 1}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}
