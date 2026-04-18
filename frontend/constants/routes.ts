/** アプリ内のユーザーロール定義 (Clerk organization roles) */
export type UserRole = "org:admin" | "org:member";

/** ルート設定の型定義 */
export interface RouteConfig {
  /** ページパス */
  path: string;
  /** 表示ラベル */
  label: string;
  /** アクセス可能なロール */
  allowedRoles: UserRole[];
  /** カード等に表示する説明文 */
  description?: string;
}

const ALL_ROLES: UserRole[] = ["org:admin", "org:member"];

/** アプリ内のルート定義 */
export const ROUTES = {
  DASHBOARD: {
    path: "/",
    label: "ダッシュボード",
    allowedRoles: ALL_ROLES,
    description: "各機能へのポータル",
  },
  SHIFTS: {
    path: "/shift-requirements",
    label: "シフト枠カレンダー",
    allowedRoles: ALL_ROLES,
    description: "シフト枠の登録・管理",
  },
  ADMIN_SETTINGS: {
    path: "/admin/settings/",
    label: "管理者設定",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "スキルランク・シフトルール・対象部門・休日設定等の管理者専用設定",
  },
  TENANT_INFO: {
    path: "/admin/settings/tenant-info",
    label: "テナント基本情報",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "組織名・Clerk Organization ID・プラン情報の確認",
  },
} as const satisfies Record<string, RouteConfig>;
