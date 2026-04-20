// frontend/app/admin/settings/page.tsx
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

type SettingsLink = {
  href: string;
  label: string;
  description: string;
  icon: string;
};

type SettingsCategory = {
  id: string;
  label: string;
  description: string;
  links: SettingsLink[];
};

const SETTINGS_CATEGORIES: SettingsCategory[] = [
  {
    id: "masters",
    label: "組織・マスタ管理",
    description: "「誰が、どこに所属しているか」を定義する土台部分",
    links: [
      {
        href: "/admin/settings/departments",
        label: "部門管理",
        description: "シフト対象の部門を管理します。",
        icon: "🏢",
      },
      {
        href: "/admin/settings/workers",
        label: "対応者管理",
        description: "シフト作成の際に割り当てる対応者を管理します。",
        icon: "👥",
      },
      {
        href: "/admin/settings/positions",
        label: "役職マスタ管理",
        description: "役職名とシフト除外フラグ（GW・SW・年末年始等）を管理します。",
        icon: "🎖️",
      },
      {
        href: "/admin/settings/employment-types",
        label: "雇用形態マスタ管理",
        description: "テナント固有の雇用形態（正職員・非常勤・特別雇用等）を定義します。",
        icon: "🗂️",
      },
    ],
  },
  {
    id: "policy",
    label: "シフト運用ルール",
    description: "「どのような条件でシフトを組むか」というロジック部分",
    links: [
      {
        href: "/admin/settings/rules",
        label: "基本ルール設定",
        description: "シフト作成時に適用されるルール・警告の設定とシフト対象部門を管理します。",
        icon: "📋",
      },
      {
        href: "/admin/settings/custom-rules",
        label: "カスタムルール管理",
        description: "Worker単位でアサイン可能なカスタムシフトルールを定義します。雇用形態ルールより優先適用されます。",
        icon: "⚙️",
      },
      {
        href: "/admin/settings/skill-ranks",
        label: "スキルランク設定",
        description: "テナント固有のスキルランクを定義します。",
        icon: "⭐",
      },
      {
        href: "/admin/settings/holidays",
        label: "休日・長期休暇設定",
        description: "テナント固有の祝日・休日と長期休暇期間（GW・シルバーウィーク・年末年始等）を管理します。",
        icon: "📅",
      },
    ],
  },
  {
    id: "reporting",
    label: "集計・ログ",
    description: "「結果の確認」と「システム管理」",
    links: [
      {
        href: "/admin/aggregate-stats",
        label: "シフト集計",
        description: "Worker単位のシフト集計（直近12ヶ月のSlotType別合計・月平均）を表示します。",
        icon: "📊",
      },
      {
        href: "/admin/settings/tenant-info",
        label: "テナント基本情報",
        description: "組織名・Clerk Organization ID・プラン情報を確認します。",
        icon: "🏷️",
      },
    ],
  },
];

export default async function SettingsIndexPage() {
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
            <span className="text-sm text-gray-700 font-medium tracking-wide">
              設定
            </span>
          </div>
        </div>
      </nav>

      {/* メインコンテンツ */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-10">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-wide">
            設定
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            各種テナント設定を管理します。
          </p>
        </div>

        {SETTINGS_CATEGORIES.map((category) => (
          <section key={category.id} aria-labelledby={`category-${category.id}`}>
            <div className="mb-4">
              <h2
                id={`category-${category.id}`}
                className="text-base font-semibold text-gray-800"
              >
                {category.label}
              </h2>
              <p className="mt-0.5 text-xs text-gray-500">{category.description}</p>
            </div>
            <ul className="space-y-3">
              {category.links.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="group flex items-center gap-4 rounded-lg border border-gray-200 bg-white px-5 py-4 transition-colors hover:border-gray-300 hover:shadow-sm"
                  >
                    <span className="text-2xl">{item.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-800 group-hover:text-blue-600 transition-colors">
                        {item.label}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500">
                        {item.description}
                      </p>
                    </div>
                    <span className="text-gray-400 group-hover:text-blue-500 transition-colors">
                      ›
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </main>
    </div>
  );
}
