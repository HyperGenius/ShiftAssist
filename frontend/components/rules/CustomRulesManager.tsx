"use client";
// frontend/components/rules/CustomRulesManager.tsx

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useCustomRules } from "@/hooks/useCustomRules";
import type { CustomRule, CustomRuleCreate, CustomRuleUpdate } from "@/types/customRule";

const SLOT_TYPE_OPTIONS = [
  { value: "weekday_night", label: "平日夜間" },
  { value: "sat_pre_hol_night", label: "土曜・祝前夜間" },
  { value: "sat_day", label: "土曜昼間" },
  { value: "sat_night", label: "土曜夜間" },
  { value: "sun_hol_day", label: "日祝昼間" },
  { value: "sun_hol_night", label: "日祝夜間" },
  { value: "long_hol_day", label: "長期休暇昼間" },
  { value: "long_hol_night", label: "長期休暇夜間" },
] as const;

/** 年間上限上書き対象の枠種別（long_hol は sun_hol に合算のため除外） */
const ANNUAL_LIMIT_SLOT_OPTIONS = [
  { value: "weekday_night", label: "平日夜間" },
  { value: "sat_pre_hol_night", label: "土曜・祝前夜間" },
  { value: "sat_day", label: "土曜昼間" },
  { value: "sat_night", label: "土曜夜間" },
  { value: "sun_hol_day", label: "日祝昼間" },
  { value: "sun_hol_night", label: "日祝夜間" },
] as const;

type AnnualLimitKey = (typeof ANNUAL_LIMIT_SLOT_OPTIONS)[number]["value"] | "annual_total";

interface RuleFormState {
  name: string;
  allowed_slot_types: string[];
  use_allowed_slot_types: boolean;
  use_annual_limit_overrides: boolean;
  /** 入力フィールドの値（空文字 = 上書きなし = グローバルルールに従う） */
  annual_limit_overrides: Record<AnnualLimitKey, string>;
}

function emptyAnnualLimitOverrides(): Record<AnnualLimitKey, string> {
  return {
    annual_total: "",
    weekday_night: "",
    sat_pre_hol_night: "",
    sat_day: "",
    sat_night: "",
    sun_hol_day: "",
    sun_hol_night: "",
  };
}

function defaultFormState(): RuleFormState {
  return {
    name: "",
    allowed_slot_types: [],
    use_allowed_slot_types: false,
    use_annual_limit_overrides: false,
    annual_limit_overrides: emptyAnnualLimitOverrides(),
  };
}

function ruleToFormState(rule: CustomRule): RuleFormState {
  const rawOverrides = rule.annual_limit_overrides;
  const hasOverrides = rawOverrides !== null && rawOverrides !== undefined &&
    Object.values(rawOverrides).some((v) => v !== null && v !== undefined);

  const overridesForForm = emptyAnnualLimitOverrides();
  if (rawOverrides) {
    for (const key of Object.keys(overridesForForm) as AnnualLimitKey[]) {
      const val = rawOverrides[key];
      overridesForForm[key] = val !== null && val !== undefined ? String(val) : "";
    }
  }

  return {
    name: rule.name,
    allowed_slot_types: rule.allowed_slot_types ?? [],
    use_allowed_slot_types: (rule.allowed_slot_types?.length ?? 0) > 0,
    use_annual_limit_overrides: hasOverrides,
    annual_limit_overrides: overridesForForm,
  };
}

/** フォームの annual_limit_overrides を API 用の Record に変換する。空文字 → null */
function buildAnnualLimitOverrides(
  formOverrides: Record<AnnualLimitKey, string>,
): Record<string, number | null> | null {
  const result: Record<string, number | null> = {};
  let hasAnyValue = false;
  for (const key of Object.keys(formOverrides) as AnnualLimitKey[]) {
    const raw = formOverrides[key].trim();
    if (raw === "") {
      result[key] = null;
    } else {
      const num = parseInt(raw, 10);
      result[key] = isNaN(num) ? null : num;
      if (!isNaN(num)) hasAnyValue = true;
    }
  }
  return hasAnyValue ? result : null;
}

interface RuleFormProps {
  initial: RuleFormState;
  onSubmit: (data: RuleFormState) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
  submitLabel: string;
}

function RuleForm({ initial, onSubmit, onCancel, isSubmitting, submitLabel }: RuleFormProps) {
  const [form, setForm] = useState<RuleFormState>(initial);

  const toggleSlotType = (value: string) => {
    setForm((prev) => {
      const has = prev.allowed_slot_types.includes(value);
      return {
        ...prev,
        allowed_slot_types: has
          ? prev.allowed_slot_types.filter((s) => s !== value)
          : [...prev.allowed_slot_types, value],
      };
    });
  };

  const setLimitOverride = (key: AnnualLimitKey, value: string) => {
    setForm((prev) => ({
      ...prev,
      annual_limit_overrides: {
        ...prev.annual_limit_overrides,
        [key]: value,
      },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    await onSubmit(form);
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
      <Input
        id="custom-rule-name"
        label="ルール名"
        placeholder="例: 日曜・祝日昼のみ可"
        value={form.name}
        onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
        disabled={isSubmitting}
        required
      />

      {/* アサイン可能な枠制限 */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.use_allowed_slot_types}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                use_allowed_slot_types: e.target.checked,
                allowed_slot_types: e.target.checked ? prev.allowed_slot_types : [],
              }))
            }
            disabled={isSubmitting}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">
            アサイン可能な枠を制限する
          </span>
        </label>

        {form.use_allowed_slot_types && (
          <div className="ml-6 grid grid-cols-2 gap-2">
            {SLOT_TYPE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-2 cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  checked={form.allowed_slot_types.includes(opt.value)}
                  onChange={() => toggleSlotType(opt.value)}
                  disabled={isSubmitting}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-600">{opt.label}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* 年間シフト回数上限の上書き */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.use_annual_limit_overrides}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                use_annual_limit_overrides: e.target.checked,
                annual_limit_overrides: e.target.checked
                  ? prev.annual_limit_overrides
                  : emptyAnnualLimitOverrides(),
              }))
            }
            disabled={isSubmitting}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">
            年間シフト回数上限を上書きする
          </span>
        </label>

        {form.use_annual_limit_overrides && (
          <div className="ml-6 space-y-3">
            <p className="text-xs text-gray-500">
              空欄の場合はグローバルルールの設定が適用されます。0 を入力すると制限なしになります。
            </p>
            {/* 合計 */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-700 w-36 shrink-0">合計（年間）</span>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  placeholder="例: 20"
                  value={form.annual_limit_overrides.annual_total}
                  onChange={(e) => setLimitOverride("annual_total", e.target.value)}
                  disabled={isSubmitting}
                  className="w-24 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
                <span className="text-xs text-gray-500">回</span>
              </div>
            </div>
            {/* 各枠種別 */}
            {ANNUAL_LIMIT_SLOT_OPTIONS.map((opt) => (
              <div key={opt.value} className="flex items-center gap-3">
                <span className="text-sm text-gray-700 w-36 shrink-0">{opt.label}</span>
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    min={0}
                    placeholder="空欄=グローバル設定"
                    value={form.annual_limit_overrides[opt.value]}
                    onChange={(e) => setLimitOverride(opt.value, e.target.value)}
                    disabled={isSubmitting}
                    className="w-24 rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                  <span className="text-xs text-gray-500">回</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          キャンセル
        </Button>
        <Button
          type="submit"
          loading={isSubmitting}
          disabled={!form.name.trim()}
        >
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}

/** カスタムルール管理テーブルUI */
export function CustomRulesManager() {
  const { customRules, isLoading, createCustomRule, updateCustomRule, deleteCustomRule } =
    useCustomRules();
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = async (formState: RuleFormState) => {
    setIsSubmitting(true);
    try {
      const payload: CustomRuleCreate = {
        name: formState.name.trim(),
        allowed_slot_types:
          formState.use_allowed_slot_types && formState.allowed_slot_types.length > 0
            ? formState.allowed_slot_types
            : null,
        annual_limit_overrides: formState.use_annual_limit_overrides
          ? buildAnnualLimitOverrides(formState.annual_limit_overrides)
          : null,
      };
      await createCustomRule(payload);
      setShowAddForm(false);
      toast.success(`カスタムルール「${payload.name}」を作成しました`);
    } catch {
      toast.error("カスタムルールの作成に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async (id: string, formState: RuleFormState) => {
    setIsSubmitting(true);
    try {
      const payload: CustomRuleUpdate = {
        name: formState.name.trim(),
        allowed_slot_types:
          formState.use_allowed_slot_types && formState.allowed_slot_types.length > 0
            ? formState.allowed_slot_types
            : null,
        annual_limit_overrides: formState.use_annual_limit_overrides
          ? buildAnnualLimitOverrides(formState.annual_limit_overrides)
          : null,
      };
      await updateCustomRule(id, payload);
      setEditingId(null);
      toast.success(`カスタムルール「${payload.name}」を更新しました`);
    } catch {
      toast.error("カスタムルールの更新に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (rule: CustomRule) => {
    if (!confirm(`カスタムルール「${rule.name}」を削除しますか？\nこのルールがアサインされているWorkerのカスタムルール設定はNULLにリセットされます。`)) return;
    setIsSubmitting(true);
    try {
      await deleteCustomRule(rule.id);
      toast.success(`カスタムルール「${rule.name}」を削除しました`);
    } catch {
      toast.error("カスタムルールの削除に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSlotTypeLabel = (value: string) =>
    SLOT_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value;

  const formatAnnualLimits = (overrides: Record<string, number | null> | null): string => {
    if (!overrides) return "";
    const parts: string[] = [];
    if (overrides.annual_total !== null && overrides.annual_total !== undefined) {
      parts.push(`合計: ${overrides.annual_total}回`);
    }
    for (const opt of ANNUAL_LIMIT_SLOT_OPTIONS) {
      const val = overrides[opt.value];
      if (val !== null && val !== undefined) {
        parts.push(`${opt.label}: ${val}回`);
      }
    }
    return parts.join("、");
  };

  if (isLoading) {
    return (
      <div className="text-sm text-gray-500">読み込み中...</div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ルール一覧 */}
      {customRules.length === 0 ? (
        <p className="text-sm text-gray-500">カスタムルールが登録されていません。</p>
      ) : (
        <ul className="divide-y divide-gray-200 border border-gray-200 rounded-lg overflow-hidden">
          {customRules.map((rule) => (
            <li key={rule.id} className="bg-white">
              {editingId === rule.id ? (
                <div className="p-4">
                  <RuleForm
                    initial={ruleToFormState(rule)}
                    onSubmit={(formState) => handleUpdate(rule.id, formState)}
                    onCancel={() => setEditingId(null)}
                    isSubmitting={isSubmitting}
                    submitLabel="更新する"
                  />
                </div>
              ) : (
                <div className="px-4 py-3 flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800">{rule.name}</p>
                    {rule.allowed_slot_types && rule.allowed_slot_types.length > 0 ? (
                      <p className="text-xs text-gray-500 mt-0.5">
                        許可枠: {rule.allowed_slot_types.map(getSlotTypeLabel).join("、")}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-400 mt-0.5">枠制限なし</p>
                    )}
                    {rule.annual_limit_overrides && formatAnnualLimits(rule.annual_limit_overrides) && (
                      <p className="text-xs text-blue-600 mt-0.5">
                        年間上限: {formatAnnualLimits(rule.annual_limit_overrides)}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingId(rule.id)}
                      disabled={isSubmitting}
                    >
                      編集
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void handleDelete(rule)}
                      disabled={isSubmitting}
                      className="text-red-600 hover:bg-red-50"
                    >
                      削除
                    </Button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* 新規追加フォーム */}
      {showAddForm ? (
        <div className="border border-gray-200 rounded-lg p-4 bg-white">
          <p className="text-sm font-medium text-gray-700 mb-3">新規カスタムルールを追加</p>
          <RuleForm
            initial={defaultFormState()}
            onSubmit={handleCreate}
            onCancel={() => setShowAddForm(false)}
            isSubmitting={isSubmitting}
            submitLabel="作成する"
          />
        </div>
      ) : (
        <Button
          variant="secondary"
          onClick={() => setShowAddForm(true)}
          disabled={isSubmitting}
        >
          ＋ カスタムルールを追加
        </Button>
      )}
    </div>
  );
}
