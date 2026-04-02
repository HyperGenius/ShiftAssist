// frontend/components/rules/RulesSettingsForm.tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiPanel } from "@/components/ui/SciFiPanel";
import { useShiftRules } from "@/hooks/useShiftRules";
import type { ShiftRules } from "@/types/shiftRules";

// ---------------------------------------------------------------------------
// Zodバリデーションスキーマ
// ---------------------------------------------------------------------------
const rulesSchema = z.object({
  min_interval_days: z
    .number()
    .int("整数を入力してください")
    .min(0, "最小勤務間隔は0以上の値を指定してください"),
  require_skill_ranks: z
    .string()
    .min(1, "必須スキルランクは少なくとも1つ入力してください"),
  allow_same_department: z.boolean(),
  special_employment_shifts: z.string(),
  workers_per_slot: z
    .number()
    .int("整数を入力してください")
    .min(1, "1スロットあたりの人数は1以上の値を指定してください"),
  avoid_consecutive_holidays: z.boolean(),
});

type RulesFormValues = z.infer<typeof rulesSchema>;

// ---------------------------------------------------------------------------
// ShiftRules ↔ フォーム値の変換ユーティリティ
// ---------------------------------------------------------------------------
function toFormValues(rules: ShiftRules): RulesFormValues {
  return {
    min_interval_days: rules.shift_rules.min_interval_days,
    require_skill_ranks: rules.shift_rules.require_skill_ranks.join(", "),
    allow_same_department: rules.shift_rules.allow_same_department,
    special_employment_shifts:
      rules.shift_rules.special_employment_shifts.join(", "),
    workers_per_slot: rules.shift_rules.workers_per_slot,
    avoid_consecutive_holidays: rules.warnings.avoid_consecutive_holidays,
  };
}

function toShiftRules(values: RulesFormValues, currentRules: ShiftRules): ShiftRules {
  return {
    shift_rules: {
      min_interval_days: values.min_interval_days,
      require_skill_ranks: values.require_skill_ranks
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      allow_same_department: values.allow_same_department,
      special_employment_shifts: values.special_employment_shifts
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      workers_per_slot: values.workers_per_slot,
      // テナント設定（/settings で管理）はそのまま引き継ぐ
      target_departments: currentRules.shift_rules.target_departments,
      target_all_departments: currentRules.shift_rules.target_all_departments,
    },
    warnings: {
      avoid_consecutive_holidays: values.avoid_consecutive_holidays,
    },
  };
}

// ---------------------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------------------
export function RulesSettingsForm() {
  const { rules, isLoading, updateRules } = useShiftRules();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingValues, setPendingValues] = useState<RulesFormValues | null>(
    null,
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<RulesFormValues>({
    resolver: zodResolver(rulesSchema),
    defaultValues: toFormValues(rules),
  });

  // rulesがロード完了したらフォームをリセット
  useEffect(() => {
    if (!isLoading) {
      reset(toFormValues(rules));
    }
  }, [rules, isLoading, reset]);

  const onFormSubmit = (values: RulesFormValues) => {
    setPendingValues(values);
    setShowConfirm(true);
  };

  const handleConfirm = async () => {
    if (!pendingValues) return;
    setShowConfirm(false);
    setIsSubmitting(true);
    try {
      await updateRules(toShiftRules(pendingValues, rules));
      toast.success("シフトルールを保存しました");
      setPendingValues(null);
    } catch {
      toast.error("シフトルールの保存に失敗しました");
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
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="h-10 rounded bg-slate-800/60 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <>
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-8">
        {/* シフトルール設定 */}
        <SciFiPanel className="p-6 space-y-6">
          <h2 className="text-sm font-semibold tracking-widest text-cyan-300 uppercase">
            シフトルール設定
          </h2>

          <SciFiInput
            id="min_interval_days"
            label="最小勤務間隔（日数）"
            type="number"
            min={0}
            {...register("min_interval_days", { valueAsNumber: true })}
            error={errors.min_interval_days?.message}
            disabled={isSubmitting}
          />

          <div className="flex flex-col gap-1">
            <label
              htmlFor="require_skill_ranks"
              className="text-xs text-slate-400 uppercase tracking-wider"
            >
              必須スキルランク（カンマ区切り）
            </label>
            <input
              id="require_skill_ranks"
              className={[
                "bg-slate-800/60 border rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500",
                "focus:outline-none focus:ring-1 focus:ring-cyan-500/70 focus:border-cyan-500/70",
                "transition-colors duration-150",
                errors.require_skill_ranks
                  ? "border-red-500/60 focus:ring-red-500/50 focus:border-red-500/50"
                  : "border-slate-600/50",
              ]
                .filter(Boolean)
                .join(" ")}
              placeholder="例: rank_a, rank_b"
              {...register("require_skill_ranks")}
              disabled={isSubmitting}
            />
            {errors.require_skill_ranks && (
              <p className="text-xs text-red-400 mt-0.5">
                {errors.require_skill_ranks.message}
              </p>
            )}
            <p className="text-xs text-slate-500 mt-0.5">
              利用可能: rank_a, rank_b, rank_c, rank_d
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              id="allow_same_department"
              type="checkbox"
              {...register("allow_same_department")}
              disabled={isSubmitting}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
            />
            <label
              htmlFor="allow_same_department"
              className="text-sm text-slate-300 cursor-pointer"
            >
              同一所属課のペアを許可する
            </label>
          </div>

          <div className="flex flex-col gap-1">
            <label
              htmlFor="special_employment_shifts"
              className="text-xs text-slate-400 uppercase tracking-wider"
            >
              特別雇用者が参加できるシフト種別（カンマ区切り）
            </label>
            <input
              id="special_employment_shifts"
              className={[
                "bg-slate-800/60 border rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500",
                "focus:outline-none focus:ring-1 focus:ring-cyan-500/70 focus:border-cyan-500/70",
                "transition-colors duration-150",
                errors.special_employment_shifts
                  ? "border-red-500/60 focus:ring-red-500/50 focus:border-red-500/50"
                  : "border-slate-600/50",
              ]
                .filter(Boolean)
                .join(" ")}
              placeholder="例: weekday_night"
              {...register("special_employment_shifts")}
              disabled={isSubmitting}
            />
            {errors.special_employment_shifts && (
              <p className="text-xs text-red-400 mt-0.5">
                {errors.special_employment_shifts.message}
              </p>
            )}
          </div>

          <SciFiInput
            id="workers_per_slot"
            label="1スロットあたりの必要人数"
            type="number"
            min={1}
            {...register("workers_per_slot", { valueAsNumber: true })}
            error={errors.workers_per_slot?.message}
            disabled={isSubmitting}
          />
        </SciFiPanel>

        {/* 警告設定 */}
        <SciFiPanel className="p-6 space-y-6">
          <h2 className="text-sm font-semibold tracking-widest text-cyan-300 uppercase">
            警告設定
          </h2>

          <div className="flex items-center gap-3">
            <input
              id="avoid_consecutive_holidays"
              type="checkbox"
              {...register("avoid_consecutive_holidays")}
              disabled={isSubmitting}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
            />
            <label
              htmlFor="avoid_consecutive_holidays"
              className="text-sm text-slate-300 cursor-pointer"
            >
              休日枠への連続アサインを警告する
            </label>
          </div>
        </SciFiPanel>

        <div className="flex justify-end">
          <SciFiButton
            type="submit"
            loading={isSubmitting}
            disabled={!isDirty || isSubmitting}
          >
            設定を保存する
          </SciFiButton>
        </div>
      </form>

      {/* 保存確認ダイアログ */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
          <SciFiPanel className="p-8 max-w-md w-full mx-4 space-y-6">
            <h3 className="text-base font-semibold text-slate-100">
              ルールの適用確認
            </h3>
            <p className="text-sm text-slate-400">
              このシフトルールを適用しますか？変更後は新しいルールに基づいてシフトバリデーションが動作します。
            </p>
            <div className="flex justify-end gap-3">
              <SciFiButton
                type="button"
                variant="ghost"
                onClick={handleCancelConfirm}
              >
                キャンセル
              </SciFiButton>
              <SciFiButton type="button" onClick={handleConfirm}>
                適用する
              </SciFiButton>
            </div>
          </SciFiPanel>
        </div>
      )}
    </>
  );
}
