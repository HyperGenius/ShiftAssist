// frontend/components/rules/RulesSettingsForm.tsx
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
  hired_tenure_months: z
    .number()
    .int("整数を入力してください")
    .min(0, "採用アサイン可能期間は0以上の値を指定してください"),
  cross_division_transfer_tenure_months: z
    .number()
    .int("整数を入力してください")
    .min(0, "事業部間転入アサイン可能期間は0以上の値を指定してください"),
  max_total_age: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  max_non_weekday_night_per_period: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_total: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_weekday_night: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_sat_day: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_sat_night: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_sun_hol_day: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_sun_hol_night: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
  annual_sat_pre_hol_night: z
    .number()
    .int("整数を入力してください")
    .min(0, "0以上の値を指定してください"),
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
    hired_tenure_months: rules.shift_rules.hired_tenure_months,
    cross_division_transfer_tenure_months:
      rules.shift_rules.cross_division_transfer_tenure_months,
    max_total_age: rules.shift_rules.max_total_age ?? 120,
    max_non_weekday_night_per_period:
      rules.shift_rules.max_non_weekday_night_per_period ?? 1,
    annual_total: rules.warnings.annual_shift_limits?.annual_total ?? 22,
    annual_weekday_night: rules.warnings.annual_shift_limits?.weekday_night ?? 10,
    annual_sat_day: rules.warnings.annual_shift_limits?.sat_day ?? 3,
    annual_sat_night: rules.warnings.annual_shift_limits?.sat_night ?? 3,
    annual_sun_hol_day: rules.warnings.annual_shift_limits?.sun_hol_day ?? 4,
    annual_sun_hol_night: rules.warnings.annual_shift_limits?.sun_hol_night ?? 5,
    annual_sat_pre_hol_night: rules.warnings.annual_shift_limits?.sat_pre_hol_night ?? 4,
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
      hired_tenure_months: values.hired_tenure_months,
      cross_division_transfer_tenure_months:
        values.cross_division_transfer_tenure_months,
      max_total_age: values.max_total_age,
      max_non_weekday_night_per_period: values.max_non_weekday_night_per_period,
    },
    warnings: {
      avoid_consecutive_holidays: values.avoid_consecutive_holidays,
      annual_shift_limits: {
        annual_total: values.annual_total,
        weekday_night: values.annual_weekday_night,
        sat_day: values.annual_sat_day,
        sat_night: values.annual_sat_night,
        sun_hol_day: values.annual_sun_hol_day,
        sun_hol_night: values.annual_sun_hol_night,
        sat_pre_hol_night: values.annual_sat_pre_hol_night,
      },
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
            className="h-10 rounded bg-gray-200 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <>
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-8">
        {/* シフトルール設定 */}
        <Panel className="p-6 space-y-6">
          <h2 className="text-sm font-semibold text-gray-700">
            シフトルール設定
          </h2>

          <Input
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
              className="text-xs font-medium text-gray-600"
            >
              必須スキルランク（カンマ区切り）
            </label>
            <input
              id="require_skill_ranks"
              className={[
                "bg-white border rounded px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
                "focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500",
                "transition-colors duration-150",
                errors.require_skill_ranks
                  ? "border-red-400 focus:ring-red-500/30 focus:border-red-500"
                  : "border-gray-300",
              ]
                .filter(Boolean)
                .join(" ")}
              placeholder="例: rank_a, rank_b"
              {...register("require_skill_ranks")}
              disabled={isSubmitting}
            />
            {errors.require_skill_ranks && (
              <p className="text-xs text-red-500 mt-0.5">
                {errors.require_skill_ranks.message}
              </p>
            )}
            <p className="text-xs text-gray-400 mt-0.5">
              利用可能: rank_a, rank_b, rank_c, rank_d
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              id="allow_same_department"
              type="checkbox"
              {...register("allow_same_department")}
              disabled={isSubmitting}
              className="h-4 w-4 rounded border-gray-300 bg-white text-blue-600 focus:ring-blue-500/50"
            />
            <label
              htmlFor="allow_same_department"
              className="text-sm text-gray-700 cursor-pointer"
            >
              同一所属課のペアを許可する
            </label>
          </div>

          {/* 特別雇用者(is_special)は廃止 */}
          {/*
          <div className="flex flex-col gap-1">
            <label
              htmlFor="special_employment_shifts"
              className="text-xs font-medium text-gray-600"
            >
              特別雇用者が参加できるシフト種別（カンマ区切り）
            </label>
            <input
              id="special_employment_shifts"
              className={[
                "bg-white border rounded px-3 py-2 text-sm text-gray-900 placeholder-gray-400",
                "focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500",
                "transition-colors duration-150",
                errors.special_employment_shifts
                  ? "border-red-400 focus:ring-red-500/30 focus:border-red-500"
                  : "border-gray-300",
              ]
                .filter(Boolean)
                .join(" ")}
              placeholder="例: weekday_night"
              {...register("special_employment_shifts")}
              disabled={isSubmitting}
            />
            {errors.special_employment_shifts && (
              <p className="text-xs text-red-500 mt-0.5">
                {errors.special_employment_shifts.message}
              </p>
            )}
          </div>
          */}

          <Input
            id="workers_per_slot"
            label="1スロットあたりの必要人数"
            type="number"
            min={1}
            {...register("workers_per_slot", { valueAsNumber: true })}
            error={errors.workers_per_slot?.message}
            disabled={isSubmitting}
          />

          <Input
            id="hired_tenure_months"
            label="採用アサイン可能期間（月）"
            type="number"
            min={0}
            {...register("hired_tenure_months", { valueAsNumber: true })}
            error={errors.hired_tenure_months?.message}
            disabled={isSubmitting}
          />

          <Input
            id="cross_division_transfer_tenure_months"
            label="事業部間転入アサイン可能期間（月）"
            type="number"
            min={0}
            {...register("cross_division_transfer_tenure_months", {
              valueAsNumber: true,
            })}
            error={errors.cross_division_transfer_tenure_months?.message}
            disabled={isSubmitting}
          />

          <Input
            id="max_total_age"
            label="合計年齢上限（歳）"
            type="number"
            min={0}
            {...register("max_total_age", { valueAsNumber: true })}
            error={errors.max_total_age?.message}
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-400 -mt-4">0 で制限なし</p>

          <Input
            id="max_non_weekday_night_per_period"
            label="平日夜間以外シフト回数上限（回/月）"
            type="number"
            min={0}
            {...register("max_non_weekday_night_per_period", {
              valueAsNumber: true,
            })}
            error={errors.max_non_weekday_night_per_period?.message}
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-400 -mt-4">0 で制限なし</p>
        </Panel>

        {/* 警告設定 */}
        <Panel className="p-6 space-y-6">
          <h2 className="text-sm font-semibold text-gray-700">
            警告設定
          </h2>

          <div className="flex items-center gap-3">
            <input
              id="avoid_consecutive_holidays"
              type="checkbox"
              {...register("avoid_consecutive_holidays")}
              disabled={isSubmitting}
              className="h-4 w-4 rounded border-gray-300 bg-white text-blue-600 focus:ring-blue-500/50"
            />
            <label
              htmlFor="avoid_consecutive_holidays"
              className="text-sm text-gray-700 cursor-pointer"
            >
              休日枠への連続アサインを警告する
            </label>
          </div>
        </Panel>

        {/* 年間シフト回数上限設定 */}
        <Panel className="p-6 space-y-6">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">
              年間シフト回数上限
            </h2>
            <p className="mt-1 text-xs text-gray-400">
              1ワーカーあたりの年間合計シフト回数の上限を設定します。0を設定すると制限なし（無制限）となります。
            </p>
          </div>

          <Input
            id="annual_total"
            label="年間総シフト回数上限（全種別合計）"
            type="number"
            min={0}
            {...register("annual_total", { valueAsNumber: true })}
            error={errors.annual_total?.message}
            disabled={isSubmitting}
          />

          <Input
            id="annual_weekday_night"
            label="年間上限: 平日夜間（weekday_night）"
            type="number"
            min={0}
            {...register("annual_weekday_night", { valueAsNumber: true })}
            error={errors.annual_weekday_night?.message}
            disabled={isSubmitting}
          />

          <Input
            id="annual_sat_pre_hol_night"
            label="年間上限: 土曜・祝前日夜間（sat_pre_hol_night）"
            type="number"
            min={0}
            {...register("annual_sat_pre_hol_night", { valueAsNumber: true })}
            error={errors.annual_sat_pre_hol_night?.message}
            disabled={isSubmitting}
          />

          <Input
            id="annual_sat_day"
            label="年間上限: 土曜昼間（sat_day）"
            type="number"
            min={0}
            {...register("annual_sat_day", { valueAsNumber: true })}
            error={errors.annual_sat_day?.message}
            disabled={isSubmitting}
          />

          <Input
            id="annual_sat_night"
            label="年間上限: 土曜夜間（sat_night）"
            type="number"
            min={0}
            {...register("annual_sat_night", { valueAsNumber: true })}
            error={errors.annual_sat_night?.message}
            disabled={isSubmitting}
          />

          <Input
            id="annual_sun_hol_day"
            label="年間上限: 日祝昼間（sun_hol_day・long_hol_day 合算）"
            type="number"
            min={0}
            {...register("annual_sun_hol_day", { valueAsNumber: true })}
            error={errors.annual_sun_hol_day?.message}
            disabled={isSubmitting}
          />

          <Input
            id="annual_sun_hol_night"
            label="年間上限: 日祝夜間（sun_hol_night・long_hol_night 合算）"
            type="number"
            min={0}
            {...register("annual_sun_hol_night", { valueAsNumber: true })}
            error={errors.annual_sun_hol_night?.message}
            disabled={isSubmitting}
          />
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
              ルールの適用確認
            </h3>
            <p className="text-sm text-gray-500">
              このシフトルールを適用しますか？変更後は新しいルールに基づいてシフトバリデーションが動作します。
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
