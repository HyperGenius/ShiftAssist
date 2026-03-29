// frontend/components/ui/SciFiPanel.tsx
import { type HTMLAttributes } from "react";

interface SciFiPanelProps extends HTMLAttributes<HTMLDivElement> {
  /** コーナーアクセントを表示するか */
  corners?: boolean;
}

export function SciFiPanel({
  corners = true,
  className = "",
  children,
  ...props
}: SciFiPanelProps) {
  return (
    <div
      className={[
        "relative bg-slate-900/80 border border-slate-700/60 rounded-lg backdrop-blur-sm",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {corners && (
        <>
          {/* コーナーアクセント */}
          <span className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-cyan-500/70 rounded-tl" />
          <span className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-cyan-500/70 rounded-tr" />
          <span className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-cyan-500/70 rounded-bl" />
          <span className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-cyan-500/70 rounded-br" />
        </>
      )}
      {children}
    </div>
  );
}
