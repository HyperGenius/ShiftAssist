"use client";

import { UserButton, useOrganization } from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { UserRole } from "@/constants/routes";
import { ROUTES } from "@/constants/routes";

/** ヘッダーナビゲーションに表示するルート */
const NAV_ROUTES = [ROUTES.DASHBOARD, ROUTES.SHIFTS] as const;

/** 全画面共通ヘッダーコンポーネント */
export function Header() {
  const { membership } = useOrganization();
  const pathname = usePathname();

  const userRole: UserRole | undefined = membership?.role as
    | UserRole
    | undefined;

  // ロールが未取得の場合（未ログイン・組織未所属）は "org:member" 相当として扱い、
  // 管理者専用ルートを非表示にする保守的なフォールバック戦略を採用する。
  const visibleNavRoutes = NAV_ROUTES.filter((route) =>
    userRole
      ? route.allowedRoles.includes(userRole)
      : route.allowedRoles.includes("org:member"),
  );

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* ブランドロゴ */}
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="text-sm font-bold tracking-widest text-gray-800 uppercase hover:text-gray-600 transition-colors"
          >
            SHIFT<span className="text-gray-400">ASSIST</span>
          </Link>

          {/* ナビゲーションリンク */}
          <nav className="hidden sm:flex items-center gap-1">
            {visibleNavRoutes.map((route) => {
              const isActive = pathname === route.path;
              return (
                <Link
                  key={route.path}
                  href={route.path}
                  className={[
                    "px-3 py-1.5 text-xs font-medium tracking-wider uppercase rounded transition-all duration-200",
                    isActive
                      ? "bg-gray-100 text-gray-800 border border-gray-300"
                      : "text-gray-500 hover:text-gray-700 hover:bg-gray-100 border border-transparent",
                  ].join(" ")}
                >
                  {route.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* ユーザーメニュー */}
        <UserButton />
      </div>
    </header>
  );
}
