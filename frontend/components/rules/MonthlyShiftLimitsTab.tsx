// frontend/components/rules/MonthlyShiftLimitsTab.tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Panel } from "@/components/ui/Panel";
import { useShiftRules } from "@/hooks/useShiftRules";
import type { ShiftRules } from "@/types/shiftRules";

// ---------------------------------------------------------------------------
// Zodバリデーションスキーマ
// ---------------------------------------------------------------------------
const monthlySchema = z.object({
  monthly_total: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  weekday_night: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  non_weekday_night: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
});

type MonthlyFormValues = z.infer<typeof monthlySchema>;

// ---------------------------------------------------------------------------
// ShiftRules ↔ フォーム値の変換ユーティリティ
// ---------------------------------------------------------------------------
function toFormValues(rules: ShiftRules): MonthlyFormValues {
  return {
    monthly_total: rules.shift_rules.monthly_shift_limits?.monthly_total ?? 2,
    weekday_night: rules.shift_rules.monthly_shift_limits?.weekday_night ?? 2,
    non_weekday_night:
      rules.shift_rules.monthly_shift_limits?.non_weekday_night ?? 1,
  };
}

function toShiftRules(
  values: MonthlyFormValues,
  currentRules: ShiftRules,
): ShiftRules {
  return {
    ...currentRules,
    shift_rules: {
      ...currentRules.shift_rules,
      monthly_shift_limits: {
        monthly_total: values.monthly_total,
        weekday_night: values.weekday_night,
        non_weekday_night: values.non_weekday_night,
      },
    },
  };
}

// ---------------------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------------------
export function MonthlyShiftLimitsTab() {
  const { rules, isLoading, updateRules } = useShiftRules();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingValues, setPendingValues] = useState<MonthlyFormValues | null>(
    null,
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<MonthlyFormValues>({
    resolver: zodResolver(monthlySchema),
    defaultValues: toFormValues(rules),
  });

  useEffect(() => {
    if (!isLoading) {
      reset(toFormValues(rules));
    }
  }, [rules, isLoading, reset]);

  const onFormSubmit = (values: MonthlyFormValues) => {
    setPendingValues(values);
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    if (!pendingValues) return;
    setShowConfirm(false);
    setIsSubmitting(true);
    try {
      await updateRules(toShiftRules(pendingValues, rules));
      toast.success("月間シフト回数上限設定を保存しました");
      setPendingValues(null);
    } catch {
      toast.error("月間シフト回数上限設定の保存に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelConfirm = () => {
    setShowConfirm(false);
    setPendingValues(null);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-10 rounded bg-gray-200 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <>
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-8">
        <Panel className="p-6 space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">
              月間シフト回数上限設定
            </h2>
            <p className="mt-1 text-xs text-gray-400">
              1ワーカーあたりの月間シフト回数の上限を設定します。0を設定すると制限なし（無制限）となります。
            </p>
          </div>

          <Input
            id="monthly_total"
            label="月間総シフト回数上限（全種別合計）"
            type="number"
            min={0}
            {...register("monthly_total", { valueAsNumber: true })}
            error={errors.monthly_total?.message}
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-400 -mt-4">0 で制限なし</p>

          <Input
            id="weekday_night"
            label="月間上限: 平日夜間（weekday_night）"
            type="number"
            min={0}
            {...register("weekday_night", { valueAsNumber: true })}
            error={errors.weekday_night?.message}
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-400 -mt-4">0 で制限なし</p>

          <Input
            id="non_weekday_night"
            label="月間上限: 平日夜間以外（sat_day / sat_night / sun_hol_day 等）"
            type="number"
            min={0}
            {...register("non_weekday_night", { valueAsNumber: true })}
            error={errors.non_weekday_night?.message}
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-400 -mt-4">0 で制限なし</p>
        </Panel>

        <div className="flex justify-end">
          <Button
            type="submit"
            loading={isSubmitting}
            disabled={!isDirty || isSubmitting}
          >
            設定を保存する
          </Button>
        </div>
      </form>

      {/* 保存確認ダイアログ */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50">
          <Panel className="p-8 max-w-md w-full mx-4 space-y-6">
            <h3 className="text-base font-semibold text-gray-900">
              設定の適用確認
            </h3>
            <p className="text-sm text-gray-500">
              月間シフト回数上限設定を適用しますか？変更後は新しい設定に基づいてシフトバリデーションが動作します。
            </p>
            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="ghost"
                onClick={handleCancelConfirm}
              >
                キャンセル
              </Button>
              <Button type="button" onClick={handleConfirm}>
                適用する
              </Button>
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}
