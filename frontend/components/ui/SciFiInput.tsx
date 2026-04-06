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
            className="text-xs font-medium text-gray-600"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={[
            "bg-white border rounded px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
            "focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500",
            "transition-colors duration-150",
            error
              ? "border-red-400 focus:ring-red-500/30 focus:border-red-500"
              : "border-gray-300",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
          {...props}
        />
        {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
      </div>
    );
  },
);

SciFiInput.displayName = "SciFiInput";

export { SciFiInput };
