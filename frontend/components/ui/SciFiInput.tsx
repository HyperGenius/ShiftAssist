// frontend/components/ui/SciFiInput.tsx
"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

interface SciFiInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const SciFiInput = forwardRef<HTMLInputElement, SciFiInputProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
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
        <input
          ref={ref}
          id={id}
          className={[
            "bg-slate-800/60 border rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500",
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
        />
        {error && <p className="text-xs text-red-400 mt-0.5">{error}</p>}
      </div>
    );
  },
);

SciFiInput.displayName = "SciFiInput";

export { SciFiInput };
