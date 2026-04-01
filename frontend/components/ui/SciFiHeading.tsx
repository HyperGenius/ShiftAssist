// frontend/components/ui/SciFiHeading.tsx
import { type HTMLAttributes } from "react";

type Level = "h1" | "h2" | "h3" | "h4";

interface SciFiHeadingProps extends HTMLAttributes<HTMLHeadingElement> {
  level?: Level;
  /** アクセントラインを表示するか */
  accent?: boolean;
}

const levelClasses: Record<Level, string> = {
  h1: "text-3xl font-bold tracking-widest",
  h2: "text-2xl font-semibold tracking-wider",
  h3: "text-xl font-semibold tracking-wide",
  h4: "text-lg font-medium tracking-wide",
};

export function SciFiHeading({
  level = "h2",
  accent = true,
  className = "",
  children,
  ...props
}: SciFiHeadingProps) {
  const Tag = level;
  return (
    <Tag
      className={[
        "text-cyan-300",
        accent && "border-b border-cyan-500/30 pb-2",
        levelClasses[level],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </Tag>
  );
}
