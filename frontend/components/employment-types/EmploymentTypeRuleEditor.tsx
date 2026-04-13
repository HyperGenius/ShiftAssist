// frontend/components/employment-types/EmploymentTypeRuleEditor.tsx
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiHeading } from "@/components/ui/SciFiHeading";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useEmploymentTypes } from "@/hooks/useEmploymentTypes";
import type {
  AnnualPartialLimitsConfig,
  EmploymentTypeRuleConfig,
  EmploymentTypeRuleUpdate,
} from "@/types/employmentType";

/** SlotTypeEnum の全値と日本語ラベル */
const SLOT_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "weekday_night", label: "平日夜間" },
  { value: "sat_day", label: "土曜昼間" },
  { value: "sat_night", label: "土曜夜間" },
  { value: "sun_hol_day", label: "日曜・祝日昼間" },
  { value: "sun_hol_night", label: "日曜・祝日夜間" },
  { value: "long_hol_day", label: "長期連休昼間" },
  { value: "long_hol_night", label: "長期連休夜間" },
  { value: "sat_pre_hol_night", label: "土曜・祝前日夜間" },
];

/** 年間上限フィールドの定義 */
const ANNUAL_LIMIT_FIELDS: { key: keyof AnnualPartialLimitsConfig; label: string }[] = [
  { key: "annual_total", label: "年間合計" },
  { key: "weekday_night", label: "平日夜間" },
  { key: "sat_day", label: "土曜昼間" },
  { key: "sat_night", label: "土曜夜間" },
  { key: "sun_hol_day", label: "日祝昼間" },
  { key: "sun_hol_night", label: "日祝夜間" },
  { key: "sat_pre_hol_night", label: "土曜・祝前日夜間" },
];

interface Props {
  employmentTypeId: string;
  employmentTypeName: string;
  onClose: () => void;
}

/** 雇用形態別ルールエディタコンポーネント */
export function EmploymentTypeRuleEditor({ employmentTypeId, employmentTypeName, onClose }: Props) {
  const { fetchEmploymentTypeRules, updateEmploymentTypeRules } = useEmploymentTypes();

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [requireDefaultPair, setRequireDefaultPair] = useState(false);
  const [allowedSlotTypes, setAllowedSlotTypes] = useState<string[]>([]);
  const [noSlotRestriction, setNoSlotRestriction] = useState(true);
  const [annualOverrides, setAnnualOverrides] = useState<Record<string, string>>({});

  useEffect(() => {
    setIsLoading(true);
    fetchEmploymentTypeRules(employmentTypeId)
      .then((rule: EmploymentTypeRuleConfig) => {
        setRequireDefaultPair(rule.require_default_pair);
        if (rule.allowed_slot_types && rule.allowed_slot_types.length > 0) {
          setNoSlotRestriction(false);
          setAllowedSlotTypes(rule.allowed_slot_types);
        } else {
          setNoSlotRestriction(true);
          setAllowedSlotTypes([]);
        }
        if (rule.annual_limit_overrides) {
          const overrides: Record<string, string> = {};
          for (const field of ANNUAL_LIMIT_FIELDS) {
            const val = rule.annual_limit_overrides[field.key];
            overrides[field.key] = val != null ? String(val) : "";
          }
          setAnnualOverrides(overrides);
        }
      })
      .catch(() => {
        toast.error("ルール設定の取得に失敗しました");
      })
      .finally(() => setIsLoading(false));
  }, [employmentTypeId, fetchEmploymentTypeRules]);

  const handleSlotTypeToggle = (value: string) => {
    setAllowedSlotTypes((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // 年間上限の上書き設定を構築
      const annual_limit_overrides: Record<string, number | null> = {};
      let hasAnyOverride = false;
      for (const field of ANNUAL_LIMIT_FIELDS) {
        const raw = annualOverrides[field.key];
        if (raw !== undefined && raw !== "") {
          annual_limit_overrides[field.key] = parseInt(raw, 10);
          hasAnyOverride = true;
        } else {
          annual_limit_overrides[field.key] = null;
        }
      }

      const payload: EmploymentTypeRuleUpdate = {
        require_default_pair: requireDefaultPair,
        allowed_slot_types: noSlotRestriction ? null : allowedSlotTypes,
        annual_limit_overrides: hasAnyOverride ? annual_limit_overrides : null,
      };

      await updateEmploymentTypeRules(employmentTypeId, payload);
      toast.success(`"${employmentTypeName}" のルール設定を保存しました`);
      onClose();
    } catch {
      toast.error("ルール設定の保存に失敗しました");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-8 rounded bg-gray-200 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SciFiHeading level="h4">「{employmentTypeName}」のルール設定</SciFiHeading>

      {/* ペア制限 */}
      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level="h4">ペア制限（require_default_pair）</SciFiHeading>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={requireDefaultPair}
            onChange={(e) => setRequireDefaultPair(e.target.checked)}
            disabled={isSaving}
            className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-gray-700">
            ペア相手にデフォルト雇用形態のスタッフが必須
          </span>
        </label>
        <p className="text-xs text-gray-400">
          有効にすると、この雇用形態のスタッフをアサインする際、同一枠にデフォルト雇用形態のスタッフが含まれていなければなりません（1人枠は除く）。
        </p>
      </SciFiPanel>

      {/* アサイン可能枠 */}
      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level="h4">アサイン可能枠（allowed_slot_types）</SciFiHeading>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={noSlotRestriction}
            onChange={(e) => {
              setNoSlotRestriction(e.target.checked);
              if (e.target.checked) setAllowedSlotTypes([]);
            }}
            disabled={isSaving}
            className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-gray-700">
            制限なし（グローバル設定に従う）
          </span>
        </label>
        {!noSlotRestriction && (
          <div className="grid grid-cols-2 gap-2 mt-2">
            {SLOT_TYPE_OPTIONS.map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={allowedSlotTypes.includes(opt.value)}
                  onChange={() => handleSlotTypeToggle(opt.value)}
                  disabled={isSaving}
                  className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">{opt.label}</span>
              </label>
            ))}
          </div>
        )}
      </SciFiPanel>

      {/* 年間シフト回数上限の上書き */}
      <SciFiPanel className="p-4 space-y-3">
        <SciFiHeading level="h4">年間シフト回数上限の上書き（annual_limit_overrides）</SciFiHeading>
        <p className="text-xs text-gray-400">
          空欄はグローバル設定に従います。0 を入力すると制限なしになります。
        </p>
        <div className="grid grid-cols-2 gap-3">
          {ANNUAL_LIMIT_FIELDS.map((field) => (
            <SciFiInput
              key={field.key}
              id={`annual-override-${field.key}`}
              label={field.label}
              type="number"
              min="0"
              placeholder="グローバル設定に従う"
              value={annualOverrides[field.key] ?? ""}
              onChange={(e) =>
                setAnnualOverrides((prev) => ({ ...prev, [field.key]: e.target.value }))
              }
              disabled={isSaving}
            />
          ))}
        </div>
      </SciFiPanel>

      <div className="flex gap-3 justify-end">
        <SciFiButton variant="ghost" onClick={onClose} disabled={isSaving}>
          キャンセル
        </SciFiButton>
        <SciFiButton loading={isSaving} onClick={() => void handleSave()}>
          保存
        </SciFiButton>
      </div>
    </div>
  );
}
