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
