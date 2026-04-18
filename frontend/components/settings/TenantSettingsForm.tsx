// frontend/components/settings/TenantSettingsForm.tsx
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { useDepartments } from "@/hooks/useDepartments";
import { useShiftRules } from "@/hooks/useShiftRules";
import type { ShiftRules } from "@/types/shiftRules";

/** テナント全体設定フォームコンポーネント */
export function TenantSettingsForm() {
  const { rules, isLoading: rulesLoading, updateRules } = useShiftRules();
  const { departments, isLoading: deptsLoading } = useDepartments();

  const [targetAllDepartments, setTargetAllDepartments] = useState(true);
  const [selectedDeptCodes, setSelectedDeptCodes] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  const isLoading = rulesLoading || deptsLoading;

  // ロード完了後にフォームを初期化
  useEffect(() => {
    if (!isLoading) {
      setTargetAllDepartments(rules.shift_rules.target_all_departments);
      setSelectedDeptCodes(rules.shift_rules.target_departments);
      setIsDirty(false);
    }
  }, [rules, isLoading]);

  const handleToggleAllDepartments = (checked: boolean) => {
    setTargetAllDepartments(checked);
    setIsDirty(true);
  };

  const handleDeptCodeChange = (code: string, checked: boolean) => {
    setSelectedDeptCodes((prev) => {
      const next = checked ? [...prev, code] : prev.filter((c) => c !== code);
      setIsDirty(true);
      return next;
    });
  };

  const handleSave = async () => {
    setIsSubmitting(true);
    try {
      const payload: ShiftRules = {
        ...rules,
        shift_rules: {
          ...rules.shift_rules,
          target_all_departments: targetAllDepartments,
          target_departments: targetAllDepartments ? [] : selectedDeptCodes,
        },
      };
      await updateRules(payload);
      setIsDirty(false);
      toast.success("テナント設定を保存しました");
    } catch {
      toast.error("テナント設定の保存に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="h-10 rounded bg-gray-200 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Panel className="p-6 space-y-6">
        <h2 className="text-sm font-semibold tracking-widest text-gray-700 uppercase">
          シフト対象部門の設定
        </h2>

        {/* 全テナント対象トグル */}
        <div className="flex items-center gap-3">
          <input
            id="target_all_departments"
            type="checkbox"
            checked={targetAllDepartments}
            onChange={(e) => handleToggleAllDepartments(e.target.checked)}
            disabled={isSubmitting}
            className="h-4 w-4 rounded border-gray-300 bg-white text-blue-600 focus:ring-blue-500/30"
          />
          <label
            htmlFor="target_all_departments"
            className="text-sm text-gray-700 cursor-pointer"
          >
            テナント全体（全課）を対象とする
          </label>
        </div>

        {/* 個別部門選択 */}
        <div
          className={`space-y-3 transition-opacity ${
            targetAllDepartments ? "opacity-40 pointer-events-none" : "opacity-100"
          }`}
        >
          <p className="text-xs text-gray-500 uppercase tracking-wider">
            シフトアサインする対象の所属課（複数選択可）
          </p>
          {departments.length === 0 ? (
            <p className="text-sm text-gray-400">
              部門が登録されていません。先に部門を登録してください。
            </p>
          ) : (
            <div className="space-y-2">
              {departments.map((dept) => (
                <div key={dept.id} className="flex items-center gap-3">
                  <input
                    id={`dept-${dept.id}`}
                    type="checkbox"
                    checked={selectedDeptCodes.includes(dept.code)}
                    onChange={(e) =>
                      handleDeptCodeChange(dept.code, e.target.checked)
                    }
                    disabled={isSubmitting || targetAllDepartments}
                    className="h-4 w-4 rounded border-gray-300 bg-white text-blue-600 focus:ring-blue-500/30"
                  />
                  <label
                    htmlFor={`dept-${dept.id}`}
                    className="text-sm text-gray-700 cursor-pointer"
                  >
                    {dept.name}
                    <span className="ml-2 text-xs text-gray-400">
                      ({dept.code})
                    </span>
                  </label>
                </div>
              ))}
            </div>
          )}
        </div>
      </Panel>

      <div className="flex justify-end">
        <Button
          type="button"
          loading={isSubmitting}
          disabled={!isDirty || isSubmitting}
          onClick={() => void handleSave()}
        >
          設定を保存する
        </Button>
      </div>
    </div>
  );
}
