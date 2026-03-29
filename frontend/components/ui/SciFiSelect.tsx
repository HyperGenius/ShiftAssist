// frontend/components/ui/SciFiSelect.tsx
"use client";

import { forwardRef, type SelectHTMLAttributes } from "react";

interface SciFiSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

const SciFiSelect = forwardRef<HTMLSelectElement, SciFiSelectProps>(
  ({ label, error, className = "", id, children, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={id}
            className="text-xs text-slate-400 uppercase tracking-wider"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={id}
          className={[
            "bg-slate-800/60 border rounded px-3 py-2 text-sm text-slate-200",
            "focus:outline-none focus:ring-1 focus:ring-cyan-500/70 focus:border-cyan-500/70",
            "transition-colors duration-150",
            error
              ? "border-red-500/60 focus:ring-red-500/50 focus:border-red-500/50"
              : "border-slate-600/50",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
          {...props}
        >
          {children}
        </select>
        {error && <p className="text-xs text-red-400 mt-0.5">{error}</p>}
      </div>
    );
  },
);

SciFiSelect.displayName = "SciFiSelect";

export { SciFiSelect };
