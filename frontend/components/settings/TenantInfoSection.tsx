// frontend/components/settings/TenantInfoSection.tsx
"use client";

import { useState } from "react";

import { Panel } from "@/components/ui/Panel";

interface TenantInfoSectionProps {
  organizationName: string;
  organizationId: string;
}

/** 組織基本情報（組織名・Clerk Organization ID）表示セクション */
export function TenantInfoSection({
  organizationName,
  organizationId,
}: TenantInfoSectionProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(organizationId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // クリップボードへのアクセスが拒否された場合は何もしない
    }
  };

  return (
    <Panel className="p-6 space-y-6">
      <h2 className="text-sm font-semibold tracking-widest text-gray-700 uppercase">
        組織基本情報
      </h2>

      {/* 組織名 */}
      <div className="space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-wider">
          組織名 (Organization Name)
        </p>
        <p className="text-sm font-medium text-gray-800">{organizationName}</p>
        <p className="text-xs text-gray-400">
          ※ 組織名の変更は Clerk ダッシュボードで行ってください。
        </p>
      </div>

      {/* Clerk Organization ID */}
      <div className="space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-wider">
          Clerk Organization ID
        </p>
        <div className="flex items-center gap-2">
          <code className="flex-1 rounded bg-gray-100 px-3 py-1.5 text-xs font-mono text-gray-700 break-all">
            {organizationId}
          </code>
          <button
            type="button"
            onClick={() => void handleCopy()}
            className="shrink-0 rounded border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-colors"
          >
            {copied ? "✓ コピー済み" : "コピー"}
          </button>
        </div>
        <p className="text-xs text-gray-400">
          ※ サポートや課金管理で使用される識別子です。
        </p>
      </div>
    </Panel>
  );
}
