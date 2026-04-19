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
    path: "/admin/settings",
    label: "設定",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "組織・マスタ管理、シフト運用ルール、集計・ログの管理者専用設定",
  },
  /** カテゴリ1: 組織・マスタ管理 */
  SETTINGS_MASTERS: {
    path: "/admin/settings",
    label: "組織・マスタ管理",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "部門・対応者・役職・雇用形態など「誰が、どこに所属しているか」を定義します",
  },
  SETTINGS_DEPARTMENTS: {
    path: "/admin/settings/departments",
    label: "部門管理",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "シフト対象の部門を管理します。",
  },
  SETTINGS_WORKERS: {
    path: "/admin/settings/workers",
    label: "対応者管理",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "シフト作成の際に割り当てる対応者を管理します。",
  },
  SETTINGS_POSITIONS: {
    path: "/admin/settings/positions",
    label: "役職マスタ管理",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "役職名とシフト除外フラグを管理します。",
  },
  SETTINGS_EMPLOYMENT_TYPES: {
    path: "/admin/settings/employment-types",
    label: "雇用形態マスタ管理",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "テナント固有の雇用形態を定義します。",
  },
  /** カテゴリ2: シフト運用ルール */
  SETTINGS_POLICY: {
    path: "/admin/settings",
    label: "シフト運用ルール",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "「どのような条件でシフトを組むか」というロジック部分を設定します",
  },
  SETTINGS_RULES: {
    path: "/admin/settings/rules",
    label: "基本ルール設定",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "シフト作成時に適用されるルール・警告の設定とシフト対象部門を管理します。",
  },
  SETTINGS_SKILL_RANKS: {
    path: "/admin/settings/skill-ranks",
    label: "スキルランク設定",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "テナント固有のスキルランクを定義します。",
  },
  SETTINGS_HOLIDAYS: {
    path: "/admin/settings/holidays",
    label: "休日・長期休暇設定",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "テナント固有の祝日・休日と長期休暇期間を管理します。",
  },
  /** カテゴリ3: 集計・ログ */
  SETTINGS_REPORTING: {
    path: "/admin/settings",
    label: "集計・ログ",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "シフトの集計結果とシステム設定を確認します",
  },
  SETTINGS_AGGREGATE_STATS: {
    path: "/admin/aggregate-stats",
    label: "シフト集計",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "Worker単位のシフト集計を表示します。",
  },
  TENANT_INFO: {
    path: "/admin/settings/tenant-info",
    label: "テナント基本情報",
    allowedRoles: ["org:admin"] as UserRole[],
    description: "組織名・Clerk Organization ID・プラン情報の確認",
  },
} as const satisfies Record<string, RouteConfig>;
