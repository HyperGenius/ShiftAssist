// frontend/components/ui/Panel.tsx
import { type HTMLAttributes } from "react";

type PanelProps = HTMLAttributes<HTMLDivElement>;

export function Panel({
  className = "",
  children,
  ...props
}: PanelProps) {
  return (
    <div
      className={[
        "relative bg-white border border-gray-200 rounded-lg shadow-sm",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </div>
  );
}
