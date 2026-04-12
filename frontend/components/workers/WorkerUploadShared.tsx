// frontend/components/workers/WorkerUploadShared.tsx
// Worker一括登録・更新パネルで共有するUIコンポーネント

/** 件数バッジ */
export function CountBadge({
  label,
  count,
  colorClass,
}: {
  label: string;
  count: number;
  colorClass: string;
}) {
  if (count === 0) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}
    >
      {label}: {count}件
    </span>
  );
}

/** ファイルアップロードアイコン */
export function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "w-10 h-10 mx-auto mb-3 text-gray-400"}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

/** 成功チェックアイコン */
export function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "w-5 h-5 text-blue-600 flex-shrink-0"}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
