// frontend/app/admin/settings/skill-ranks/page.tsx
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import { SkillRankSettingsForm } from "@/components/skill-ranks/SkillRankSettingsForm";

export default async function SkillRanksSettingsPage() {
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
              スキルランク設定
            </span>
          </div>
          <UserButton />
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-wide">
            スキルランク設定
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            テナント固有のスキルランクを定義します。ランク名はスタッフ登録・一覧画面に反映されます。
          </p>
        </div>

        <SkillRankSettingsForm />
      </main>
    </div>
  );
}
