// frontend/components/ui/Heading.tsx
import { type HTMLAttributes } from "react";

type Level = "h1" | "h2" | "h3" | "h4";

interface HeadingProps extends HTMLAttributes<HTMLHeadingElement> {
  level?: Level;
  /** アクセントラインを表示するか */
  accent?: boolean;
}

const levelClasses: Record<Level, string> = {
  h1: "text-3xl font-bold tracking-tight",
  h2: "text-2xl font-semibold tracking-tight",
  h3: "text-xl font-semibold",
  h4: "text-lg font-medium",
};

export function Heading({
  level = "h2",
  accent = true,
  className = "",
  children,
  ...props
}: HeadingProps) {
  const Tag = level;
  return (
    <Tag
      className={[
        "text-gray-900",
        accent && "border-b border-gray-200 pb-2",
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
