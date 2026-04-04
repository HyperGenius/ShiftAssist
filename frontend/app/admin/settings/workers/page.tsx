// frontend/app/workers/page.tsx
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { WorkerList } from "@/components/workers/WorkerList";
import Link from "next/dist/client/link";

export default async function WorkersPage() {
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
              対応者管理
            </span>
          </div>
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <WorkerList />
      </main>
    </div>
  );
}
