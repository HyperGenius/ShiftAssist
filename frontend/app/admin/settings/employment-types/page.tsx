// frontend/app/admin/settings/employment-types/page.tsx
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import { EmploymentTypeSettingsForm } from "@/components/employment-types/EmploymentTypeSettingsForm";

export default async function EmploymentTypesSettingsPage() {
  const { userId } = await auth();

  if (!userId) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ナビゲーションバー */}
      <nav className="border-b border-gray-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/admin/settings"
              className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
            >
              管理者設定
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-sm text-gray-700 font-medium">
              雇用形態マスタ管理
            </span>
          </div>
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-wide">
            雇用形態マスタ管理
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            テナント固有の雇用形態を定義します。スタッフの雇用形態として割り当てられます。
          </p>
        </div>

        <EmploymentTypeSettingsForm />
      </main>
    </div>
  );
}
