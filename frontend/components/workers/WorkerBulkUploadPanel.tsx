// frontend/components/workers/WorkerBulkUploadPanel.tsx
// JSONファイルを使ったWorkerデータの一括登録・更新UIコンポーネント
"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import { useWorkers } from "@/hooks/useWorkers";
import type {
  WorkerBulkItem,
  WorkerBulkPreviewItem,
  WorkerBulkPreviewResponse,
} from "@/types/worker";
import { ApiError } from "@/utils/apiClient";

const ACTION_LABELS: Record<WorkerBulkPreviewItem["action"], string> = {
  create: "新規追加",
  update: "更新",
  no_change: "変更なし",
};

const ACTION_COLORS: Record<WorkerBulkPreviewItem["action"], string> = {
  create: "text-blue-600",
  update: "text-yellow-400",
  no_change: "text-gray-400",
};

/** プレビュー差分テーブル */
function PreviewTable({
  preview,
}: {
  preview: WorkerBulkPreviewItem[];
}) {
  return (
    <div className="overflow-x-auto max-h-64 overflow-y-auto">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-gray-50">
          <tr className="border-b border-gray-200">
            <th className="px-3 py-2 text-gray-500 font-medium">アクション</th>
            <th className="px-3 py-2 text-gray-500 font-medium">社員番号</th>
            <th className="px-3 py-2 text-gray-500 font-medium">氏名</th>
            <th className="px-3 py-2 text-gray-500 font-medium">課コード</th>
            <th className="px-3 py-2 text-gray-500 font-medium">変更前</th>
          </tr>
        </thead>
        <tbody>
          {preview.map((item) => (
            <tr
              key={item.employee_no}
              className="border-b border-gray-100 hover:bg-gray-50"
            >
              <td className={`px-3 py-2 font-semibold ${ACTION_COLORS[item.action]}`}>
                {ACTION_LABELS[item.action]}
              </td>
              <td className="px-3 py-2 text-gray-700 font-mono">{item.employee_no}</td>
              <td className="px-3 py-2 text-gray-800">{item.name}</td>
              <td className="px-3 py-2 text-gray-700 font-mono">
                {item.department_code}
                {item.department_is_new && (
                  <span className="ml-1 text-xs text-blue-600">（新規）</span>
                )}
              </td>
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

interface WorkerBulkUploadPanelProps {
  /** パネルを閉じるコールバック */
  onClose?: () => void;
}

/** WorkerデータのJSON一括登録・更新パネル */
export function WorkerBulkUploadPanel({ onClose }: WorkerBulkUploadPanelProps) {
  const { previewBulkUpload, bulkUploadWorkers } = useWorkers();
  const { skillRanks } = useSkillRanks();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedItems, setParsedItems] = useState<WorkerBulkItem[] | null>(null);
  const [preview, setPreview] = useState<WorkerBulkPreviewResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  /** スキルランクIDのセット（バリデーション用） */
  const validSkillRankIds = useMemo(
    () => new Set(skillRanks.map((r) => r.id)),
    [skillRanks],
  );

  /** JSON文字列をパースして検証する */
  const parseJson = useCallback(
    (jsonText: string): WorkerBulkItem[] | null => {
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
          'JSONはオブジェクトの配列である必要があります。',
        );
        return null;
      }

      const items: WorkerBulkItem[] = [];
      for (let i = 0; i < parsed.length; i++) {
        const item = parsed[i] as Record<string, unknown>;
        if (
          typeof item !== "object" ||
          item === null ||
          typeof item.employee_no !== "string" ||
          typeof item.name !== "string" ||
          typeof item.department_code !== "string" ||
          typeof item.skill_rank_id !== "string"
        ) {
          setParseError(
            `配列の${i + 1}番目の要素に "employee_no", "name", "department_code", "skill_rank_id" フィールド（すべて文字列）が必要です。`,
          );
          return null;
        }
        if (!item.employee_no.trim()) {
          setParseError(`配列の${i + 1}番目の要素の "employee_no" が空です。`);
          return null;
        }
        if (!item.name.trim()) {
          setParseError(`配列の${i + 1}番目の要素の "name" が空です。`);
          return null;
        }
        if (!item.department_code.trim()) {
          setParseError(`配列の${i + 1}番目の要素の "department_code" が空です。`);
          return null;
        }
        if (validSkillRankIds.size > 0 && !validSkillRankIds.has(item.skill_rank_id)) {
          setParseError(
            `配列の${i + 1}番目の要素の "skill_rank_id"（${item.skill_rank_id}）が見つかりません。`,
          );
          return null;
        }
        items.push({
          employee_no: item.employee_no.trim(),
          name: item.name.trim(),
          department_code: item.department_code.trim(),
          department_name:
            typeof item.department_name === "string" ? item.department_name.trim() || null : null,
          skill_rank_id: item.skill_rank_id,
          is_special: typeof item.is_special === "boolean" ? item.is_special : false,
          joined_at:
            typeof item.joined_at === "string" ? item.joined_at : null,
        });
      }

      if (items.length === 0) {
        setParseError("JSONに1件以上のデータが必要です。");
        return null;
      }

      return items;
    },
    [validSkillRankIds],
  );

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
      const result = await previewBulkUpload({ workers: parsedItems });
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
      const result = await bulkUploadWorkers({ workers: parsedItems });
      const parts: string[] = [];
      if (result.created > 0) parts.push(`新規追加: ${result.created}件`);
      if (result.updated > 0) parts.push(`更新: ${result.updated}件`);
      if (result.departments_created > 0)
        parts.push(`課を自動作成: ${result.departments_created}件`);
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
  }, [parsedItems, bulkUploadWorkers, onClose]);

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
        <br />
        未登録の課コード（department_code）は自動で作成されます。
      </p>
      <pre className="text-xs text-gray-500 bg-gray-50 rounded px-3 py-2 mb-4 font-mono border border-gray-200 font-mono overflow-x-auto">
        {`[
  {
    "employee_no": "EMP001",
    "name": "田中 太郎",
    "department_code": "dept_1",
    "department_name": "1課",
    "skill_rank_id": "<UUID>",
    "is_special": false
  }
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
            <span>{parsedItems.length}件のデータが読み込まれました。</span>
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
                  label="更新"
                  count={preview.update_count}
                  colorClass="bg-yellow-500/20 text-yellow-300 border border-yellow-500/40"
                />
                <CountBadge
                  label="変更なし"
                  count={preview.no_change_count}
                  colorClass="bg-gray-100 text-gray-500 border border-gray-200"
                />
                <CountBadge
                  label="課を自動作成"
                  count={preview.new_department_count}
                  colorClass="bg-purple-500/20 text-purple-300 border border-purple-500/40"
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
