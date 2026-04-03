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
  WORKERS: {
    path: "/workers",
    label: "対応者リスト",
    allowedRoles: ALL_ROLES,
    description: "対応者の登録・管理",
  },
  TENANT_SETTINGS: {
    path: "/settings",
    label: "テナント設定",
    allowedRoles: ALL_ROLES,
    description: "テナントの基本設定",
  },
  ADMIN_SETTINGS: {
    path: "/admin/settings/skill-ranks",
    label: "管理者設定",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "スキルランク・シフトルール等の管理者専用設定",
  },
} as const satisfies Record<string, RouteConfig>;
