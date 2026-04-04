// frontend/components/workers/WorkerCsvUploadPanel.tsx
// CSV/Excelファイルを使ったWorkerデータの一括登録・更新UIコンポーネント
"use client";

import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useWorkers } from "@/hooks/useWorkers";
import type {
  WorkerUploadDiffItem,
  WorkerUploadErrorRow,
  WorkerUploadPreviewResponse,
} from "@/types/worker";

const ACTION_LABELS: Record<WorkerUploadDiffItem["action"], string> = {
  create: "新規追加",
  update: "更新",
  no_change: "変更なし",
};

const ACTION_COLORS: Record<WorkerUploadDiffItem["action"], string> = {
  create: "text-cyan-400",
  update: "text-yellow-400",
  no_change: "text-slate-500",
};

/** 差分値セル（更新前 / 更新後の比較表示） */
function DiffCell({
  before,
  after,
  action,
}: {
  before: string | null | undefined;
  after: string | null | undefined;
  action: WorkerUploadDiffItem["action"];
}) {
  const hasChange = action === "update" && before !== after && after != null;
  if (!after) return <span className="text-slate-600">—</span>;
  if (!hasChange) return <span className="text-slate-300">{after}</span>;
  return (
    <span className="inline-flex flex-col gap-0.5">
      <span className="text-slate-500 line-through text-xs">{before ?? "—"}</span>
      <span className="text-yellow-300 font-semibold">{after}</span>
    </span>
  );
}

/** 差分プレビューテーブル */
function DiffTable({ diffItems }: { diffItems: WorkerUploadDiffItem[] }) {
  if (diffItems.length === 0) return null;
  return (
    <div className="overflow-x-auto max-h-72 overflow-y-auto">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-slate-800">
          <tr className="border-b border-slate-700/60">
            <th className="px-3 py-2 text-slate-400 font-medium">行</th>
            <th className="px-3 py-2 text-slate-400 font-medium">アクション</th>
            <th className="px-3 py-2 text-slate-400 font-medium">職員番号</th>
            <th className="px-3 py-2 text-slate-400 font-medium">氏名</th>
            <th className="px-3 py-2 text-slate-400 font-medium">課名</th>
            <th className="px-3 py-2 text-slate-400 font-medium">役職名</th>
            <th className="px-3 py-2 text-slate-400 font-medium">生年月日</th>
            <th className="px-3 py-2 text-slate-400 font-medium">異動種別</th>
          </tr>
        </thead>
        <tbody>
          {diffItems.map((item) => (
            <tr
              key={`${item.employee_code}-${item.row_index}`}
              className="border-b border-slate-700/30 hover:bg-slate-800/40"
            >
              <td className="px-3 py-2 text-slate-500 font-mono">{item.row_index}</td>
              <td className={`px-3 py-2 font-semibold ${ACTION_COLORS[item.action]}`}>
                {ACTION_LABELS[item.action]}
              </td>
              <td className="px-3 py-2 text-slate-300 font-mono">{item.employee_code}</td>
              <td className="px-3 py-2">
                <DiffCell
                  before={item.before?.name}
                  after={item.after.name}
                  action={item.action}
                />
              </td>
              <td className="px-3 py-2">
                <DiffCell
                  before={item.before?.department_name}
                  after={item.after.department_name}
                  action={item.action}
                />
              </td>
              <td className="px-3 py-2">
                <DiffCell
                  before={item.before?.position_name}
                  after={item.after.position_name}
                  action={item.action}
                />
              </td>
              <td className="px-3 py-2">
                <DiffCell
                  before={item.before?.birth_date}
                  after={item.after.birth_date}
                  action={item.action}
                />
              </td>
              <td className="px-3 py-2">
                <DiffCell
                  before={item.before?.transfer_type}
                  after={item.after.transfer_type}
                  action={item.action}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** エラー行テーブル */
function ErrorTable({ errorRows }: { errorRows: WorkerUploadErrorRow[] }) {
  if (errorRows.length === 0) return null;
  return (
    <div className="overflow-x-auto max-h-48 overflow-y-auto rounded border border-red-500/30 bg-red-500/5">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-slate-800">
          <tr className="border-b border-red-500/30">
            <th className="px-3 py-2 text-red-400 font-medium">行</th>
            <th className="px-3 py-2 text-red-400 font-medium">職員番号</th>
            <th className="px-3 py-2 text-red-400 font-medium">エラー内容</th>
          </tr>
        </thead>
        <tbody>
          {errorRows.map((row) => (
            <tr
              key={`error-${row.row_index}`}
              className="border-b border-red-500/20"
            >
              <td className="px-3 py-2 text-red-300 font-mono">{row.row_index}</td>
              <td className="px-3 py-2 text-red-300 font-mono">
                {row.employee_code ?? "—"}
              </td>
              <td className="px-3 py-2 text-red-300">
                <ul className="list-disc list-inside space-y-0.5">
                  {row.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
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

interface WorkerCsvUploadPanelProps {
  /** パネルを閉じるコールバック */
  onClose?: () => void;
}

/** Worker CSV/Excel一括登録・更新パネル */
export function WorkerCsvUploadPanel({ onClose }: WorkerCsvUploadPanelProps) {
  const { previewUploadFile, executeUploadFile } = useWorkers();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [preview, setPreview] = useState<WorkerUploadPreviewResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleFileSelect = useCallback((file: File) => {
    const isSupported =
      file.name.endsWith(".csv") ||
      file.name.endsWith(".xlsx") ||
      file.type === "text/csv" ||
      file.type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    if (!isSupported) {
      setUploadError("CSV（.csv）またはExcel（.xlsx）ファイルのみ対応しています。");
      return;
    }
    setSelectedFile(file);
    setUploadError(null);
    setPreview(null);
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFileSelect(file);
      e.target.value = "";
    },
    [handleFileSelect],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragging(false), []);

  const handlePreview = useCallback(async () => {
    if (!selectedFile) return;
    setIsPreviewing(true);
    setUploadError(null);
    try {
      const result = await previewUploadFile(selectedFile);
      setPreview(result);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "プレビューの取得に失敗しました");
    } finally {
      setIsPreviewing(false);
    }
  }, [selectedFile, previewUploadFile]);

  const handleExecute = useCallback(async () => {
    if (!selectedFile) return;
    setIsExecuting(true);
    try {
      const result = await executeUploadFile(selectedFile);
      const parts: string[] = [];
      if (result.created > 0) parts.push(`新規追加: ${result.created}件`);
      if (result.updated > 0) parts.push(`更新: ${result.updated}件`);
      toast.success(`一括登録・更新完了: ${parts.join(" / ")}`);
      setSelectedFile(null);
      setPreview(null);
      onClose?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "一括登録・更新に失敗しました");
    } finally {
      setIsExecuting(false);
    }
  }, [selectedFile, executeUploadFile, onClose]);

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setPreview(null);
    setUploadError(null);
  }, []);

  return (
    <SciFiPanel className="p-6">
      <div className="flex items-center justify-between mb-4">
        <SciFiHeading level="h3">一括登録・更新（CSV/Excelアップロード）</SciFiHeading>
        {onClose && (
          <SciFiButton variant="ghost" size="sm" onClick={onClose}>
            ✕
          </SciFiButton>
        )}
      </div>

      <p className="text-xs text-slate-400 mb-2">
        以下の列を含むCSV（.csv）またはExcel（.xlsx）ファイルをアップロードしてください。
      </p>
      <div className="text-xs text-slate-400 bg-slate-800/60 rounded px-3 py-2 mb-4 font-mono overflow-x-auto">
        <span className="text-cyan-400">必須:</span> 職員番号, 氏名
        <br />
        <span className="text-slate-500">任意:</span>{" "}
        生年月日, 現在のスキル取得日, 役職名, 支所名, 課名, 異動種別, 異動予定月,
        事業本部変更の有無, スキルランク名
      </div>

      {/* ドラッグ＆ドロップ エリア */}
      {!selectedFile && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={[
            "border-2 border-dashed rounded-lg px-6 py-10 text-center cursor-pointer transition-colors",
            isDragging
              ? "border-cyan-400 bg-cyan-500/10"
              : "border-slate-600 hover:border-slate-500",
          ].join(" ")}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          aria-label="CSV/Excelファイルをドラッグ＆ドロップ、またはクリックして選択"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
        >
          <svg
            className="w-10 h-10 mx-auto mb-3 text-slate-500"
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
          <p className="text-sm text-slate-400">
            CSV/Excelファイルをここにドラッグ＆ドロップ
          </p>
          <p className="text-xs text-slate-500 mt-1">またはクリックしてファイルを選択（.csv / .xlsx）</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* エラー表示 */}
      {uploadError && (
        <div className="mt-3 rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <strong>エラー:</strong> {uploadError}
          <button
            className="ml-2 underline text-red-300 hover:text-red-200"
            onClick={handleReset}
          >
            やり直す
          </button>
        </div>
      )}

      {/* ファイル選択後の操作 */}
      {selectedFile && !uploadError && (
        <div className="mt-4 space-y-4">
          <div className="flex items-center gap-3 text-sm text-slate-300">
            <svg
              className="w-5 h-5 text-cyan-400 flex-shrink-0"
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
            <span>{selectedFile.name} が選択されました。</span>
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
            <div className="space-y-4">
              {/* 件数サマリー */}
              <div className="flex flex-wrap gap-2">
                <CountBadge
                  label="新規追加"
                  count={preview.create_count}
                  colorClass="bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                />
                <CountBadge
                  label="更新"
                  count={preview.update_count}
                  colorClass="bg-yellow-500/20 text-yellow-300 border border-yellow-500/40"
                />
                <CountBadge
                  label="変更なし"
                  count={preview.no_change_count}
                  colorClass="bg-slate-700/40 text-slate-400 border border-slate-600/40"
                />
                {preview.error_count > 0 && (
                  <CountBadge
                    label="エラー"
                    count={preview.error_count}
                    colorClass="bg-red-500/20 text-red-300 border border-red-500/40"
                  />
                )}
              </div>

              {/* エラー行 */}
              {preview.has_errors && (
                <div>
                  <p className="text-xs text-red-400 mb-2 font-semibold">
                    ⚠ バリデーションエラーがある行（修正が必要です）
                  </p>
                  <ErrorTable errorRows={preview.error_rows} />
                </div>
              )}

              {/* 差分テーブル */}
              {preview.diff_items.length > 0 && (
                <div>
                  {preview.has_errors && (
                    <p className="text-xs text-slate-400 mb-2">
                      エラーのない行の差分プレビュー（エラー行はUpsert時にスキップされます）
                    </p>
                  )}
                  <DiffTable diffItems={preview.diff_items} />
                </div>
              )}

              {/* 実行ボタン */}
              <div className="flex items-center gap-3 pt-2">
                <SciFiButton
                  onClick={handleExecute}
                  loading={isExecuting}
                  disabled={isExecuting || preview.has_errors}
                  title={preview.has_errors ? "エラーがある行が含まれています。ファイルを修正してください。" : undefined}
                >
                  確定（Upsert実行）
                </SciFiButton>
                <SciFiButton variant="secondary" onClick={handleReset}>
                  キャンセル
                </SciFiButton>
                {preview.has_errors && (
                  <span className="text-xs text-red-400">
                    エラー行を修正してから再アップロードしてください
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </SciFiPanel>
  );
}
