// frontend/components/ui/SciFiPanel.tsx
import { type HTMLAttributes } from "react";

type SciFiPanelProps = HTMLAttributes<HTMLDivElement>;

export function SciFiPanel({
  className = "",
  children,
  ...props
}: SciFiPanelProps) {
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
