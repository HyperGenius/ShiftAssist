// frontend/app/settings/page.tsx
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import { TenantSettingsForm } from "@/components/settings/TenantSettingsForm";

export default async function SettingsPage() {
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
            <Link
              href="/"
              className="text-sm font-semibold tracking-widest text-cyan-300 uppercase hover:text-cyan-200 transition-colors"
            >
              ShiftAssist
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-sm text-slate-400 tracking-wide">
              テナント設定
            </span>
          </div>
          <UserButton />
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-wide">
            テナント全体設定
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            シフト作成の対象とする部門など、テナント全体に関わる基本設定を管理します。
          </p>
        </div>

        <TenantSettingsForm />
      </main>
    </div>
  );
}
