"use client";

import { useState } from "react";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import type { SlotType } from "@/types/shiftRequirement";
import type { ValidationViolation } from "@/utils/shiftValidators";
import type { ValidationMap } from "@/hooks/useShiftValidation";

const SLOT_TYPE_FULL_LABELS: Record<SlotType, string> = {
  weekday_night: "平日夜間",
  sat_day: "土曜昼間",
  sat_night: "土曜夜間",
  sun_hol_day: "日祝昼間",
  sun_hol_night: "日祝夜間",
  long_hol_day: "長期連休昼間",
  long_hol_night: "長期連休夜間",
};

interface ViolationEntry {
  dateStr: string;
  slotType: SlotType;
  violations: ValidationViolation[];
}

interface OverrideConfirmDialogProps {
  /** ダイアログを表示するか */
  isOpen: boolean;
  /** バリデーション違反マップ（スロットキー → 違反リスト） */
  violations: ValidationMap;
  /** キャンセル時のコールバック */
  onCancel: () => void;
  /** 強制保存を承諾した際のコールバック */
  onConfirm: () => void;
}

/** シフトルール違反の強制保存確認ダイアログ */
export function OverrideConfirmDialog({
  isOpen,
  violations,
  onCancel,
  onConfirm,
}: OverrideConfirmDialogProps) {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!isOpen) return null;

  // バリデーション違反をエントリリストに変換
  const entries: ViolationEntry[] = Object.entries(violations)
    .filter(([, vs]) => vs.length > 0)
    .map(([key, vs]) => {
      const [dateStr, slotType] = key.split("__") as [string, SlotType];
      return { dateStr, slotType, violations: vs };
    })
    .sort((a, b) => a.dateStr.localeCompare(b.dateStr));

  const hasErrors = entries.some((e) =>
    e.violations.some((v) => v.severity === "error"),
  );
  const hasWarnings = entries.some((e) =>
    e.violations.some((v) => v.severity === "warning"),
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <SciFiPanel className="w-full max-w-lg mx-4 p-6" corners>
        {/* タイトル */}
        <div className="mb-4">
          <h2 className="text-base font-semibold tracking-widest text-yellow-400 uppercase">
            ⚠ ルール違反の検出
          </h2>
          <p className="mt-1 text-xs text-slate-400">
            以下のシフト枠にルール違反が検出されました。内容を確認の上、強制保存を行う場合は承諾してください。
          </p>
        </div>

        {/* 違反リスト */}
        <div className="max-h-64 overflow-y-auto mb-4 space-y-2">
          {entries.map(({ dateStr, slotType, violations: vs }) => (
            <div
              key={`${dateStr}__${slotType}`}
              className="rounded border border-slate-700/60 bg-slate-800/50 px-3 py-2"
            >
              <div className="text-xs font-semibold text-cyan-300 mb-1">
                {dateStr} — {SLOT_TYPE_FULL_LABELS[slotType] ?? slotType}
              </div>
              <ul className="space-y-0.5">
                {vs.map((v, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs">
                    <span
                      className={
                        v.severity === "error"
                          ? "text-red-400 shrink-0"
                          : "text-yellow-400 shrink-0"
                      }
                    >
                      {v.severity === "error" ? "✗" : "△"}
                    </span>
                    <span className="text-slate-300">{v.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* 違反サマリーバッジ */}
        <div className="flex gap-2 mb-4 text-xs">
          {hasErrors && (
            <span className="rounded px-2 py-0.5 bg-red-500/20 text-red-300 border border-red-500/40">
              エラー あり
            </span>
          )}
          {hasWarnings && (
            <span className="rounded px-2 py-0.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">
              警告 あり
            </span>
          )}
        </div>

        {/* 承諾チェックボックス */}
        <label className="flex items-start gap-2 cursor-pointer mb-5 group">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 accent-cyan-500 cursor-pointer"
          />
          <span className="text-xs text-slate-300 group-hover:text-slate-200 transition-colors">
            上記のルール違反を確認し、現場での合意に基づき強制保存することに承諾します。
          </span>
        </label>

        {/* ボタン群 */}
        <div className="flex justify-end gap-3">
          <SciFiButton variant="secondary" size="sm" onClick={onCancel}>
            キャンセル
          </SciFiButton>
          <SciFiButton
            variant="danger"
            size="sm"
            disabled={!acknowledged}
            onClick={() => {
              setAcknowledged(false);
              onConfirm();
            }}
          >
            承諾して強制保存
          </SciFiButton>
        </div>
      </SciFiPanel>
    </div>
  );
}
