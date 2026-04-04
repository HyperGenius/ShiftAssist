// frontend/app/admin/settings/page.tsx
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

const SETTINGS_LINKS = [
  {
    href: "/admin/settings/holidays",
    label: "休日カレンダー設定",
    description: "テナント固有の祝日・休日を管理します。",
    icon: "📅",
  },
  {
    href: "/admin/settings/rules",
    label: "シフトルール設定",
    description: "シフト作成時に適用されるルールと警告の設定を管理します。",
    icon: "📋",
  },
  {
    href: "/admin/settings/skill-ranks",
    label: "スキルランク設定",
    description: "テナント固有のスキルランクを定義します。",
    icon: "⭐",
  },
  {
    href: "/admin/settings/departments",
    label: "部門管理",
    description: "シフト対象の部門を管理します。",
    icon: "🏢",
  },
  {
    href: "/admin/settings/workers",
    label: "対応者管理",
    description: "シフト作成の際に割り当てる対応者を管理します。",
    icon: "👥",
  }
] as const;

export default async function SettingsIndexPage() {
  const { userId } = await auth();

  if (!userId) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* ナビゲーションバー */}
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400 tracking-wide">
              管理者設定
            </span>
          </div>
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-wide">
            管理者設定
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            各種テナント設定を管理します。
          </p>
        </div>

        <ul className="space-y-3">
          {SETTINGS_LINKS.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="group flex items-center gap-4 rounded-lg border border-slate-700/60 bg-slate-900/80 px-5 py-4 transition-colors hover:border-cyan-500/50 hover:bg-slate-800/80"
              >
                <span className="text-2xl">{item.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors">
                    {item.label}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {item.description}
                  </p>
                </div>
                <span className="text-slate-600 group-hover:text-cyan-500 transition-colors">
                  ›
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
