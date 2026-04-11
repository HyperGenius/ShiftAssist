// frontend/components/aggregate-stats/YearMonthPicker.tsx
// 年月セレクターコンポーネント
"use client";

const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

function buildYearOptions(): number[] {
  const currentYear = new Date().getFullYear();
  // 過去3年分 + 当年
  const years: number[] = [];
  for (let y = currentYear - 3; y <= currentYear; y++) {
    years.push(y);
  }
  return years;
}

interface YearMonthPickerProps {
  id?: string;
  value: string; // YYYY-MM
  onChange: (yearMonth: string) => void;
}

export function YearMonthPicker({ id, value, onChange }: YearMonthPickerProps) {
  const [year, month] = value.split("-").map(Number);
  const yearOptions = buildYearOptions();

  function handleYearChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newYear = e.target.value;
    const paddedMonth = String(month).padStart(2, "0");
    onChange(`${newYear}-${paddedMonth}`);
  }

  function handleMonthChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newMonth = String(e.target.value).padStart(2, "0");
    onChange(`${year}-${newMonth}`);
  }

  return (
    <div id={id} className="flex items-center gap-2">
      <select
        value={year}
        onChange={handleYearChange}
        className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="年"
      >
        {yearOptions.map((y) => (
          <option key={y} value={y}>
            {y}年
          </option>
        ))}
      </select>
      <select
        value={month}
        onChange={handleMonthChange}
        className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="月"
      >
        {MONTHS.map((m) => (
          <option key={m} value={m}>
            {m}月
          </option>
        ))}
      </select>
    </div>
  );
}
