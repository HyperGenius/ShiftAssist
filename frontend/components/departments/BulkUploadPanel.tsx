// frontend/components/departments/BulkUploadPanel.tsx
// JSONファイルを使った課データの一括登録・更新UIコンポーネント
"use client";

import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useDepartments } from "@/hooks/useDepartments";
import type {
  DepartmentBulkItem,
  DepartmentBulkPreviewItem,
  DepartmentBulkPreviewResponse,
} from "@/types/department";
import { ApiError } from "@/utils/apiClient";

const ACTION_LABELS: Record<DepartmentBulkPreviewItem["action"], string> = {
  create: "新規追加",
  update: "名称変更",
  reactivate: "再活性化",
  no_change: "変更なし",
};

const ACTION_COLORS: Record<DepartmentBulkPreviewItem["action"], string> = {
  create: "text-blue-600",
  update: "text-yellow-400",
  reactivate: "text-green-400",
  no_change: "text-gray-400",
};

/** プレビュー差分テーブル */
function PreviewTable({
  preview,
}: {
  preview: DepartmentBulkPreviewItem[];
}) {
  return (
    <div className="overflow-x-auto max-h-64 overflow-y-auto">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-gray-50">
          <tr className="border-b border-gray-200">
            <th className="px-3 py-2 text-gray-500 font-medium">アクション</th>
            <th className="px-3 py-2 text-gray-500 font-medium">コード</th>
            <th className="px-3 py-2 text-gray-500 font-medium">名称</th>
            <th className="px-3 py-2 text-gray-500 font-medium">変更前</th>
          </tr>
        </thead>
        <tbody>
          {preview.map((item) => (
            <tr
              key={item.code}
              className="border-b border-gray-100 hover:bg-gray-50"
            >
              <td className={`px-3 py-2 font-semibold ${ACTION_COLORS[item.action]}`}>
                {ACTION_LABELS[item.action]}
              </td>
              <td className="px-3 py-2 text-gray-700 font-mono">{item.code}</td>
              <td className="px-3 py-2 text-gray-800">{item.name}</td>
              <td className="px-3 py-2 text-gray-400">
                {item.old_name ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 件数バッジ */
function CountBadge({
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

interface BulkUploadPanelProps {
  /** パネルを閉じるコールバック */
  onClose?: () => void;
}

/** 課データの一括登録・更新パネル */
export function BulkUploadPanel({ onClose }: BulkUploadPanelProps) {
  const { previewBulkUpload, bulkUploadDepartments } = useDepartments();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedItems, setParsedItems] = useState<DepartmentBulkItem[] | null>(null);
  const [preview, setPreview] = useState<DepartmentBulkPreviewResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  /** JSON文字列をパースして検証する */
  const parseJson = useCallback((jsonText: string): DepartmentBulkItem[] | null => {
    setParseError(null);
    setPreview(null);
    setParsedItems(null);

    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonText);
    } catch {
      setParseError("JSONの形式が不正です。有効なJSONファイルをアップロードしてください。");
      return null;
    }

    if (!Array.isArray(parsed)) {
      setParseError(
        'JSONはオブジェクトの配列（例: [{"name": "1課", "code": "dept_1"}]）である必要があります。',
      );
      return null;
    }

    const items: DepartmentBulkItem[] = [];
    for (let i = 0; i < parsed.length; i++) {
      const item = parsed[i] as Record<string, unknown>;
      if (
        typeof item !== "object" ||
        item === null ||
        typeof item.name !== "string" ||
        typeof item.code !== "string"
      ) {
        setParseError(
          `配列の${i + 1}番目の要素に "name"（文字列）と "code"（文字列）フィールドが必要です。`,
        );
        return null;
      }
      if (!item.name.trim()) {
        setParseError(`配列の${i + 1}番目の要素の "name" が空です。`);
        return null;
      }
      if (!item.code.trim()) {
        setParseError(`配列の${i + 1}番目の要素の "code" が空です。`);
        return null;
      }
      items.push({ name: item.name.trim(), code: item.code.trim() });
    }

    if (items.length === 0) {
      setParseError("JSONに1件以上のデータが必要です。");
      return null;
    }

    return items;
  }, []);

  /** ファイルを読み込んでパースする */
  const processFile = useCallback(
    (file: File) => {
      if (!file.name.endsWith(".json") && file.type !== "application/json") {
        setParseError("JSONファイル（.json）のみ対応しています。");
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const items = parseJson(text);
        if (items) {
          setParsedItems(items);
        }
      };
      reader.onerror = () => {
        setParseError("ファイルの読み込みに失敗しました。");
      };
      reader.readAsText(file);
    },
    [parseJson],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
      // 同じファイルを再選択できるようにリセット
      e.target.value = "";
    },
    [processFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  /** プレビューを取得する */
  const handlePreview = useCallback(async () => {
    if (!parsedItems) return;
    setIsPreviewing(true);
    try {
      const result = await previewBulkUpload({ departments: parsedItems });
      setPreview(result);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "プレビューの取得に失敗しました";
      setParseError(message);
    } finally {
      setIsPreviewing(false);
    }
  }, [parsedItems, previewBulkUpload]);

  /** 一括登録・更新を実行する */
  const handleExecute = useCallback(async () => {
    if (!parsedItems) return;
    setIsExecuting(true);
    try {
      const result = await bulkUploadDepartments({ departments: parsedItems });
      const parts: string[] = [];
      if (result.created > 0) parts.push(`新規追加: ${result.created}件`);
      if (result.updated > 0) parts.push(`更新: ${result.updated}件`);
      if (result.reactivated > 0) parts.push(`再活性化: ${result.reactivated}件`);
      toast.success(`一括登録・更新完了: ${parts.join(" / ")}`);
      setParsedItems(null);
      setPreview(null);
      onClose?.();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "一括登録・更新に失敗しました";
      toast.error(message);
    } finally {
      setIsExecuting(false);
    }
  }, [parsedItems, bulkUploadDepartments, onClose]);

  const handleReset = useCallback(() => {
    setParsedItems(null);
    setPreview(null);
    setParseError(null);
  }, []);

  return (
    <SciFiPanel className="p-6">
      <div className="flex items-center justify-between mb-4">
        <SciFiHeading level="h3">一括登録・更新（JSONアップロード）</SciFiHeading>
        {onClose && (
          <SciFiButton variant="ghost" size="sm" onClick={onClose}>
            ✕
          </SciFiButton>
        )}
      </div>

      {/* JSONフォーマット例 */}
      <p className="text-xs text-gray-500 mb-3">
        以下のJSON形式のファイルをアップロードしてください。
      </p>
      <pre className="text-xs text-gray-500 bg-gray-50 rounded px-3 py-2 mb-4 border border-gray-200 font-mono overflow-x-auto">
        {`[
  { "name": "1課", "code": "dept_1" },
  { "name": "2課", "code": "dept_2" }
]`}
      </pre>

      {/* ドラッグ＆ドロップ エリア */}
      {!parsedItems && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={[
            "border-2 border-dashed rounded-lg px-6 py-10 text-center cursor-pointer transition-colors",
            isDragging
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-gray-400",
          ].join(" ")}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          aria-label="JSONファイルをドラッグ＆ドロップ、またはクリックして選択"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
        >
          <svg
            className="w-10 h-10 mx-auto mb-3 text-gray-400"
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
          <p className="text-sm text-gray-500">
            JSONファイルをここにドラッグ＆ドロップ
          </p>
          <p className="text-xs text-gray-400 mt-1">またはクリックしてファイルを選択</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* エラー表示 */}
      {parseError && (
        <div className="mt-3 rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <strong>エラー:</strong> {parseError}
          <button
            className="ml-2 underline text-red-300 hover:text-red-200"
            onClick={handleReset}
          >
            やり直す
          </button>
        </div>
      )}

      {/* パース成功後の操作 */}
      {parsedItems && !parseError && (
        <div className="mt-4 space-y-4">
          <div className="flex items-center gap-3 text-sm text-gray-700">
            <svg
              className="w-5 h-5 text-blue-600 flex-shrink-0"
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
            <span>
              {parsedItems.length}件のデータが読み込まれました。
            </span>
            <SciFiButton variant="ghost" size="sm" onClick={handleReset}>
              やり直す
            </SciFiButton>
          </div>

          {/* プレビュー未取得時 */}
          {!preview && (
            <SciFiButton
              onClick={handlePreview}
              loading={isPreviewing}
              disabled={isPreviewing}
            >
              差分をプレビュー
            </SciFiButton>
          )}

          {/* プレビュー表示 */}
          {preview && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <CountBadge
                  label="新規追加"
                  count={preview.create_count}
                  colorClass="bg-blue-50 text-blue-600 border border-blue-300"
                />
                <CountBadge
                  label="名称変更"
                  count={preview.update_count}
                  colorClass="bg-yellow-500/20 text-yellow-300 border border-yellow-500/40"
                />
                <CountBadge
                  label="再活性化"
                  count={preview.reactivate_count}
                  colorClass="bg-green-500/20 text-green-300 border border-green-500/40"
                />
                <CountBadge
                  label="変更なし"
                  count={preview.no_change_count}
                  colorClass="bg-gray-100 text-gray-500 border border-gray-200"
                />
              </div>

              <PreviewTable preview={preview.preview} />

              <div className="flex items-center gap-3 pt-2">
                <SciFiButton
                  onClick={handleExecute}
                  loading={isExecuting}
                  disabled={isExecuting}
                >
                  実行する
                </SciFiButton>
                <SciFiButton variant="secondary" onClick={handleReset}>
                  キャンセル
                </SciFiButton>
              </div>
            </div>
          )}
        </div>
      )}
    </SciFiPanel>
  );
}
