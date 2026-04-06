// frontend/components/ui/ValidationBadge.tsx
// バリデーション違反バッジ＆ツールチップコンポーネント
"use client";

import { useState } from "react";

import type { ValidationViolation } from "@/utils/shiftValidators";

interface ValidationBadgeProps {
  violations: ValidationViolation[];
}

/** バリデーション違反バッジ＆ツールチップコンポーネント */
export function ValidationBadge({ violations }: ValidationBadgeProps) {
  const [tooltipVisible, setTooltipVisible] = useState(false);

  if (violations.length === 0) return null;

  const hasErrors = violations.some((v) => v.severity === "error");

  const badgeClass = hasErrors
    ? "bg-red-500/90 border-red-400 text-white"
    : "bg-yellow-500/90 border-yellow-400 text-white";

  const icon = hasErrors ? "✕" : "⚠";

  return (
    <div className="relative inline-flex">
      <button
        type="button"
        className={`rounded-full w-4 h-4 text-[9px] font-bold flex items-center justify-center border ${badgeClass} cursor-pointer`}
        onMouseEnter={() => setTooltipVisible(true)}
        onMouseLeave={() => setTooltipVisible(false)}
        aria-label={`バリデーション違反 ${violations.length}件`}
      >
        {icon}
      </button>

      {tooltipVisible && (
        <div
          role="tooltip"
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-60 rounded border border-gray-200 bg-white shadow-lg p-2 text-xs"
        >
          {violations.map((v, i) => (
            <div
              key={`${v.code}_${v.workerIds.join("_")}_${i}`}
              className={`flex items-start gap-1 ${i > 0 ? "mt-1 border-t border-gray-100 pt-1" : ""}`}
            >
              <span
                className={`shrink-0 font-bold ${v.severity === "error" ? "text-red-500" : "text-yellow-600"}`}
              >
                {v.severity === "error" ? "[ERROR]" : "[WARN]"}
              </span>
              <span className="text-gray-700">{v.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
