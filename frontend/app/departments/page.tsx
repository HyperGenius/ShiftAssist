// frontend/app/departments/page.tsx
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { DepartmentList } from "@/components/departments/DepartmentList";

export default async function DepartmentsPage() {
  const { userId } = await auth();

  if (!userId) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* ナビゲーションバー */}
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <span className="text-sm font-semibold tracking-widest text-cyan-300 uppercase">
            ShiftAssist
          </span>
          <UserButton />
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <DepartmentList />
      </main>
    </div>
  );
}
