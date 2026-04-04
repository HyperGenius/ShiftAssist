// frontend/app/admin/settings/holidays/page.tsx
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import { HolidayCalendarForm } from "@/components/holidays/HolidayCalendarForm";

export default async function HolidaysSettingsPage() {
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
              href="/admin/settings"
              className="text-sm text-slate-400 tracking-wide hover:text-slate-200 transition-colors"
            >
              管理者設定
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-sm text-slate-400 tracking-wide">
              休日カレンダー設定
            </span>
          </div>
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-wide">
            休日カレンダー設定
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            テナント固有の祝日・休日を管理します。初回アクセス時に日本の標準祝日が自動投入されます。
          </p>
        </div>

        <HolidayCalendarForm />
      </main>
    </div>
  );
}
