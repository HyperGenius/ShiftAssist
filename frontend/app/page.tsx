"use client";

import { useOrganization } from "@clerk/nextjs";
import Link from "next/link";

import { Heading } from "@/components/ui/Heading";
import { Panel } from "@/components/ui/Panel";
import type { UserRole } from "@/constants/routes";
import { ROUTES } from "@/constants/routes";

/** ダッシュボードに表示するルート（ヘッダーリンク＋設定系）*/
const DASHBOARD_ROUTES = [
  ROUTES.SHIFTS,
  ROUTES.ADMIN_SETTINGS,
] as const;

/** ダッシュボードページ */
export default function DashboardPage() {
  const { membership } = useOrganization();

  const userRole: UserRole | undefined = membership?.role as
    | UserRole
    | undefined;

  // ロールが未取得の場合（未ログイン・組織未所属）は "org:member" 相当として扱い、
  // 管理者専用ルートを非表示にする保守的なフォールバック戦略を採用する。
  const visibleRoutes = DASHBOARD_ROUTES.filter((route) =>
    userRole
      ? route.allowedRoles.includes(userRole)
      : route.allowedRoles.includes("org:member"),
  );

  return (
    <main className="flex flex-col flex-1 max-w-6xl mx-auto w-full px-4 py-10 gap-8">
      {/* ページタイトル */}
      <div>
        <Heading level="h1">ダッシュボード</Heading>
        <p className="mt-2 text-sm text-gray-500">
          各機能へのポータルです。利用する機能を選択してください。
        </p>
      </div>

      {/* 機能カード一覧 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {visibleRoutes.map((route) => (
          <Link key={route.path} href={route.path} className="group">
            <Panel className="p-6 h-full transition-all duration-200 hover:border-gray-300 hover:shadow-md">
              <h2 className="text-base font-semibold text-gray-800 group-hover:text-blue-600 transition-colors">
                {route.label}
              </h2>
              {route.description && (
                <p className="mt-2 text-sm text-gray-500">
                  {route.description}
                </p>
              )}
              <span className="mt-4 inline-block text-xs text-gray-400 group-hover:text-blue-500 transition-colors">
                開く →
              </span>
            </Panel>
          </Link>
        ))}
      </div>
    </main>
  );
}
