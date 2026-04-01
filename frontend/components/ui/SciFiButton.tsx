// frontend/components/ui/SciFiButton.tsx
"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

interface SciFiButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 hover:bg-cyan-500/30 hover:border-cyan-400 hover:shadow-[0_0_12px_rgba(6,182,212,0.4)]",
  secondary:
    "bg-slate-700/40 text-slate-300 border border-slate-600/50 hover:bg-slate-700/60 hover:border-slate-500",
  danger:
    "bg-red-500/20 text-red-300 border border-red-500/50 hover:bg-red-500/30 hover:border-red-400 hover:shadow-[0_0_12px_rgba(239,68,68,0.4)]",
  ghost:
    "bg-transparent text-slate-400 border border-transparent hover:bg-slate-700/30 hover:text-slate-300",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

const SciFiButton = forwardRef<HTMLButtonElement, SciFiButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      className = "",
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={[
          "relative inline-flex items-center justify-center gap-2 rounded font-medium tracking-wider uppercase transition-all duration-200 cursor-pointer",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        {...props}
      >
        {loading && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  },
);

SciFiButton.displayName = "SciFiButton";

export { SciFiButton };
