// frontend/components/ui/WorkerAttributeBadge.tsx
// ワーカー属性バッジ（有効月数・雇用形態）＋ Tooltip コンポーネント
"use client";

import { useState } from "react";

interface InfoBadgeProps {
  /** ツールチップに表示するテキスト（例: "有効月数: 8ヶ月"） */
  tooltip: string;
}

/** 有効月数が12ヶ月未満の場合に表示する ⓘ バッジ */
export function InfoBadge({ tooltip }: InfoBadgeProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span className="relative inline-flex">
      <span
        role="img"
        aria-label="情報"
        className="ml-1 cursor-default select-none text-blue-500 text-xs"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      >
        ⓘ
      </span>
      <span
        role="tooltip"
        aria-live="polite"
        className={`absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 shadow-lg transition-opacity ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
      >
        {tooltip}
      </span>
    </span>
  );
}

interface EmploymentTypeBadgeProps {
  /** バッジに表示する雇用形態名（例: "非常勤"） */
  label: string;
  /** ツールチップに表示するテキスト（例: "非常勤"） */
  tooltip: string;
}

/** 非デフォルト雇用形態または特別雇用者に表示するバッジ */
export function EmploymentTypeBadge({ label, tooltip }: EmploymentTypeBadgeProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span className="relative inline-flex">
      <span
        role="img"
        aria-label={`雇用形態: ${label}`}
        className="ml-1 cursor-default select-none rounded bg-amber-100 px-1 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-300"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      >
        {label}
      </span>
      <span
        role="tooltip"
        aria-live="polite"
        className={`absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 shadow-lg transition-opacity ${visible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
      >
        {tooltip}
      </span>
    </span>
  );
}
