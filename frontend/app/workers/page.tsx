// frontend/app/workers/page.tsx
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { WorkerList } from "@/components/workers/WorkerList";

export default async function WorkersPage() {
  const { userId } = await auth();

  if (!userId) {
    redirect("/");
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* メインコンテンツ */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <WorkerList />
      </main>
    </div>
  );
}
