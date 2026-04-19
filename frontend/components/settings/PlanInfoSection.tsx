// frontend/components/settings/PlanInfoSection.tsx
import { Panel } from "@/components/ui/Panel";

/** プラン情報表示セクション（初期実装：Freeプラン固定） */
export function PlanInfoSection() {
  return (
    <Panel className="p-6 space-y-6">
      <h2 className="text-sm font-semibold tracking-widest text-gray-700 uppercase">
        プラン情報
      </h2>

      {/* 現在のプラン */}
      <div className="space-y-2">
        <p className="text-xs text-gray-500 uppercase tracking-wider">
          現在のプラン
        </p>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
            Free
          </span>
          <p className="text-sm text-gray-500">無料プランをご利用中です。</p>
        </div>
      </div>

      {/* アップグレード・問い合わせリンク */}
      <div className="border-t border-gray-100 pt-4 space-y-2">
        <p className="text-xs text-gray-500">
          プランのアップグレードや機能に関するお問い合わせは、サポートまでご連絡ください。
        </p>
        <a
          href="mailto:support@example.com"
          className="inline-flex items-center text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
        >
          サポートに問い合わせる →
        </a>
      </div>
    </Panel>
  );
}
