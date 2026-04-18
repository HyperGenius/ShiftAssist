// frontend/components/workers/WorkerCsvUploadPanel.tsx
// CSV/Excelファイルを使ったWorkerデータの一括登録・更新UIコンポーネント
"use client";

import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Heading } from "@/components/ui/Heading";
import { Panel } from "@/components/ui/Panel";
import { useWorkers } from "@/hooks/useWorkers";
import type {
  WorkerUploadDiffItem,
  WorkerUploadErrorRow,
  WorkerUploadPreviewResponse,
} from "@/types/worker";
import { CheckIcon, CountBadge, UploadIcon } from "./WorkerUploadShared";

const ACTION_LABELS: Record<WorkerUploadDiffItem["action"], string> = {
  create: "新規追加",
  update: "更新",
  no_change: "変更なし",
};

const ACTION_COLORS: Record<WorkerUploadDiffItem["action"], string> = {
  create: "text-blue-600",
  update: "text-yellow-400",
  no_change: "text-gray-400",
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
  if (!after) return <span className="text-gray-400">—</span>;
  if (!hasChange) return <span className="text-gray-700">{after}</span>;
  return (
    <span className="inline-flex flex-col gap-0.5">
      <span className="text-gray-400 line-through text-xs">{before ?? "—"}</span>
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
        <thead className="sticky top-0 bg-gray-50">
          <tr className="border-b border-gray-200">
            <th className="px-3 py-2 text-gray-500 font-medium">行</th>
            <th className="px-3 py-2 text-gray-500 font-medium">アクション</th>
            <th className="px-3 py-2 text-gray-500 font-medium">職員番号</th>
            <th className="px-3 py-2 text-gray-500 font-medium">氏名</th>
            <th className="px-3 py-2 text-gray-500 font-medium">課名</th>
            <th className="px-3 py-2 text-gray-500 font-medium">役職名</th>
            <th className="px-3 py-2 text-gray-500 font-medium">生年月日</th>
            <th className="px-3 py-2 text-gray-500 font-medium">異動種別</th>
            <th className="px-3 py-2 text-gray-500 font-medium">雇用形態名</th>
          </tr>
        </thead>
        <tbody>
          {diffItems.map((item) => (
            <tr
              key={`${item.employee_code}-${item.row_index}`}
              className="border-b border-gray-100 hover:bg-gray-50"
            >
              <td className="px-3 py-2 text-gray-400 font-mono">{item.row_index}</td>
              <td className={`px-3 py-2 font-semibold ${ACTION_COLORS[item.action]}`}>
                {ACTION_LABELS[item.action]}
              </td>
              <td className="px-3 py-2 text-gray-700 font-mono">{item.employee_code}</td>
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
              <td className="px-3 py-2">
                <DiffCell
                  before={item.before?.employment_type_name}
                  after={item.after.employment_type_name}
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
        <thead className="sticky top-0 bg-gray-50">
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
    <Panel className="p-6">
      <div className="flex items-center justify-between mb-4">
        <Heading level="h3">一括登録・更新（CSV/Excelアップロード）</Heading>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        )}
      </div>

      <p className="text-xs text-gray-500 mb-2">
        以下の列を含むCSV（.csv）またはExcel（.xlsx）ファイルをアップロードしてください。
      </p>
      <div className="text-xs text-gray-500 bg-gray-50 rounded px-3 py-2 mb-4 font-mono overflow-x-auto">
        <span className="text-blue-600">必須:</span> 職員番号, 氏名
        <br />
        <span className="text-gray-400">任意:</span>{" "}
        生年月日, 現在のスキル取得日, 役職名, 支所名, 課名, 異動種別, 異動予定月,
        事業本部変更の有無, スキルランク名, 雇用形態名
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
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-gray-400",
          ].join(" ")}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          aria-label="CSV/Excelファイルをドラッグ＆ドロップ、またはクリックして選択"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
        >
          <UploadIcon />
          <p className="text-sm text-gray-500">
            CSV/Excelファイルをここにドラッグ＆ドロップ
          </p>
          <p className="text-xs text-gray-400 mt-1">またはクリックしてファイルを選択（.csv / .xlsx）</p>
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
          <div className="flex items-center gap-3 text-sm text-gray-700">
            <CheckIcon />
            <span>{selectedFile.name} が選択されました。</span>
            <Button variant="ghost" size="sm" onClick={handleReset}>
              やり直す
            </Button>
          </div>

          {/* プレビュー未取得時 */}
          {!preview && (
            <Button
              onClick={handlePreview}
              loading={isPreviewing}
              disabled={isPreviewing}
            >
              差分をプレビュー
            </Button>
          )}

          {/* プレビュー表示 */}
          {preview && (
            <div className="space-y-4">
              {/* 件数サマリー */}
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
                    <p className="text-xs text-gray-500 mb-2">
                      エラーのない行の差分プレビュー（エラー行はUpsert時にスキップされます）
                    </p>
                  )}
                  <DiffTable diffItems={preview.diff_items} />
                </div>
              )}

              {/* 実行ボタン */}
              <div className="flex items-center gap-3 pt-2">
                <Button
                  onClick={handleExecute}
                  loading={isExecuting}
                  disabled={isExecuting || preview.has_errors}
                  title={preview.has_errors ? "エラーがある行が含まれています。ファイルを修正してください。" : undefined}
                >
                  確定（Upsert実行）
                </Button>
                <Button variant="secondary" onClick={handleReset}>
                  キャンセル
                </Button>
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
    </Panel>
  );
}
