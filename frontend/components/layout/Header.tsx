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
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* ブランドロゴ */}
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="text-sm font-bold tracking-widest text-cyan-300 uppercase hover:text-cyan-200 transition-colors"
          >
            SHIFT<span className="text-slate-400">ASSIST</span>
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
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/50"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/40 border border-transparent",
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
