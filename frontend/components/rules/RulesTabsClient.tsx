// frontend/components/rules/RulesTabsClient.tsx
"use client";

import { useState } from "react";
import type { ReactNode } from "react";

const TABS = [
  { id: "shift-rules", label: "シフトルール設定" },
  { id: "tenant-settings", label: "シフト対象部門設定" },
  { id: "monthly-limits", label: "月間シフト回数上限設定" },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface RulesTabsClientProps {
  shiftRulesTab: ReactNode;
  tenantSettingsTab: ReactNode;
  monthlyLimitsTab: ReactNode;
}

export function RulesTabsClient({
  shiftRulesTab,
  tenantSettingsTab,
  monthlyLimitsTab,
}: RulesTabsClientProps) {
  const [activeTab, setActiveTab] = useState<TabId>("shift-rules");

  const tabContent: Record<TabId, ReactNode> = {
    "shift-rules": shiftRulesTab,
    "tenant-settings": tenantSettingsTab,
    "monthly-limits": monthlyLimitsTab,
  };

  return (
    <div>
      {/* タブナビゲーション */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-0" aria-label="ルール設定タブ">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={[
                "px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                activeTab === tab.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
              ].join(" ")}
              aria-selected={activeTab === tab.id}
              role="tab"
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* タブコンテンツ */}
      <div className="mt-6">{tabContent[activeTab]}</div>
    </div>
  );
}
