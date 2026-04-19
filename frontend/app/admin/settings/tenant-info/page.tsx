// frontend/app/admin/settings/tenant-info/page.tsx
import { auth, clerkClient } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import { PlanInfoSection } from "@/components/settings/PlanInfoSection";
import { TenantInfoSection } from "@/components/settings/TenantInfoSection";

export default async function TenantInfoPage() {
  const { userId, orgId } = await auth();

  if (!userId) {
    redirect("/");
  }

  if (!orgId) {
    redirect("/admin/settings");
  }

  const client = await clerkClient();
  const organization = await client.organizations.getOrganization({
    organizationId: orgId,
  });

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
              テナント基本情報
            </span>
          </div>
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-8">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-wide">
            テナント基本情報
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            組織の基本情報とプランを確認できます。
          </p>
        </div>

        <section aria-labelledby="tenant-info-heading" className="space-y-4">
          <h2
            id="tenant-info-heading"
            className="text-base font-semibold text-gray-800 border-b border-gray-200 pb-2"
          >
            基本情報
          </h2>
          <TenantInfoSection
            organizationName={organization.name}
            organizationId={organization.id}
          />
        </section>

        <section aria-labelledby="plan-info-heading" className="space-y-4">
          <h2
            id="plan-info-heading"
            className="text-base font-semibold text-gray-800 border-b border-gray-200 pb-2"
          >
            プラン情報
          </h2>
          <PlanInfoSection />
        </section>
      </main>
    </div>
  );
}
