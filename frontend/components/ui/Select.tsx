// frontend/components/ui/Select.tsx
"use client";

import { forwardRef, type SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, className = "", id, children, ...props }, ref) => {
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
        <select
          ref={ref}
          id={id}
          className={[
            "bg-white border rounded px-3 py-2 text-sm text-gray-900",
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
        >
          {children}
        </select>
        {error && <p className="text-xs text-red-500 mt-0.5">{error}</p>}
      </div>
    );
  },
);

Select.displayName = "Select";

export { Select };
