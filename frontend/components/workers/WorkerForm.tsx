"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useCustomRules } from "@/hooks/useCustomRules";
import { useDepartments } from "@/hooks/useDepartments";
import { useEmploymentTypes } from "@/hooks/useEmploymentTypes";
import { usePositions } from "@/hooks/usePositions";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import type { Worker, WorkerCreate } from "@/types/worker";

const TRANSFER_TYPE_OPTIONS = [
  { value: "", label: "選択してください" },
  { value: "no_transfer", label: "異動なし" },
  { value: "transfer_in", label: "転入" },
  { value: "transfer_out", label: "転出" },
  { value: "hired", label: "採用" },
] as const;

const workerSchema = z.object({
  name: z
    .string()
    .min(1, "氏名は必須です")
    .max(100, "氏名は100文字以内で入力してください"),
  employee_code: z.string().optional().nullable(),
  department_id: z.string().uuid("有効な所属課IDを入力してください"),
  skill_rank_id: z.string().uuid("スキルランクを選択してください"),
  position_id: z.string().uuid("役職を選択してください").optional().nullable(),
  employment_type_id: z
    .string()
    .uuid("雇用形態を選択してください")
    .optional()
    .nullable(),
  custom_rule_id: z
    .string()
    .uuid("カスタムルールを選択してください")
    .optional()
    .nullable(),
  birth_date: z.string().optional().nullable(),
  skill_acquired_at: z.string().optional().nullable(),
  transfer_type: z
    .enum(["", "no_transfer", "transfer_in", "transfer_out", "hired"])
    .optional()
    .nullable(),
  transfer_scheduled_month: z.string().optional().nullable(),
  is_cross_division_transfer: z.boolean().optional().nullable(),
  joined_at: z.string().optional().nullable(),
});

type WorkerFormValues = z.infer<typeof workerSchema>;

interface WorkerFormProps {
  /** 編集対象 Worker（新規作成時は undefined）*/
  worker?: Worker;
  /** フォーム送信ハンドラー */
  onSubmit: (data: WorkerCreate) => Promise<void>;
  /** キャンセルハンドラー */
  onCancel: () => void;
  /** 送信中フラグ */
  isSubmitting?: boolean;
}

export function WorkerForm({
  worker,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: WorkerFormProps) {
  const { departments, isLoading: isDepartmentsLoading } = useDepartments();
  const { skillRanks, isLoading: isSkillRanksLoading } = useSkillRanks();
  const { positions, isLoading: isPositionsLoading } = usePositions();
  const { employmentTypes, isLoading: isEmploymentTypesLoading } =
    useEmploymentTypes();
  const { customRules, isLoading: isCustomRulesLoading } = useCustomRules();
  const {
    register,
    handleSubmit,
    reset,
    control,
    setValue,
    formState: { errors },
  } = useForm<WorkerFormValues>({
    resolver: zodResolver(workerSchema),
    defaultValues: {
      name: worker?.name ?? "",
      employee_code: worker?.employee_code ?? "",
      department_id: worker?.department_id ?? "",
      skill_rank_id: worker?.skill_rank_id ?? "",
      position_id: worker?.position_id ?? "",
      employment_type_id: worker?.employment_type_id ?? "",
      custom_rule_id: worker?.custom_rule_id ?? "",
      birth_date: worker?.birth_date ?? "",
      skill_acquired_at: worker?.skill_acquired_at ?? "",
      transfer_type: worker?.transfer_type ?? null,
      transfer_scheduled_month: worker?.transfer_scheduled_month ?? "",
      is_cross_division_transfer: worker?.is_cross_division_transfer ?? false,
      joined_at: worker?.joined_at ?? "",
    },
  });

  const transferType = useWatch({ control, name: "transfer_type" });

  // 異動種別が変わったら関連フィールドをクリア
  useEffect(() => {
    if (transferType !== "transfer_out") {
      setValue("transfer_scheduled_month", null);
    }
    if (transferType !== "transfer_in" && transferType !== "hired") {
      setValue("joined_at", null);
    }
    if (transferType !== "transfer_in") {
      setValue("is_cross_division_transfer", false);
    }
  }, [transferType, setValue]);

  // worker が切り替わったとき、またはマスターデータ取得完了後にフォームをリセット
  useEffect(() => {
    if (
      isDepartmentsLoading ||
      isSkillRanksLoading ||
      isPositionsLoading ||
      isEmploymentTypesLoading ||
      isCustomRulesLoading
    ) {
      return;
    }
    reset({
      name: worker?.name ?? "",
      employee_code: worker?.employee_code ?? "",
      department_id: worker?.department_id ?? "",
      skill_rank_id: worker?.skill_rank_id ?? "",
      position_id: worker?.position_id ?? "",
      employment_type_id: worker?.employment_type_id ?? "",
      custom_rule_id: worker?.custom_rule_id ?? "",
      birth_date: worker?.birth_date ?? "",
      skill_acquired_at: worker?.skill_acquired_at ?? "",
      transfer_type: worker?.transfer_type ?? null,
      transfer_scheduled_month: worker?.transfer_scheduled_month ?? "",
      is_cross_division_transfer: worker?.is_cross_division_transfer ?? false,
      joined_at: worker?.joined_at ?? "",
    });
  }, [
    worker,
    reset,
    isDepartmentsLoading,
    isSkillRanksLoading,
    isPositionsLoading,
    isEmploymentTypesLoading,
    isCustomRulesLoading,
  ]);

  const handleFormSubmit = async (values: WorkerFormValues) => {
    const rawTransferType = values.transfer_type;
    const transferType = rawTransferType === "" || !rawTransferType
      ? null
      : rawTransferType as import("@/types/worker").TransferType;
    await onSubmit({
      ...values,
      employee_code: values.employee_code || null,
      position_id: values.position_id || null,
      employment_type_id: values.employment_type_id || null,
      custom_rule_id: values.custom_rule_id || null,
      birth_date: values.birth_date || null,
      skill_acquired_at: values.skill_acquired_at || null,
      transfer_type: transferType,
      transfer_scheduled_month: values.transfer_scheduled_month || null,
      is_cross_division_transfer: values.is_cross_division_transfer ?? false,
      joined_at: values.joined_at || null,
    });
  };

  const isEditing = !!worker;

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className="flex flex-col gap-4"
    >
      <Input
        id="worker-name"
        label="氏名"
        placeholder="例: 山田 太郎"
        {...register("name")}
        error={errors.name?.message}
        disabled={isSubmitting}
      />

      <Input
        id="worker-employee-code"
        label="職員番号"
        placeholder="例: EMP001"
        {...register("employee_code")}
        error={errors.employee_code?.message}
        disabled={isSubmitting}
      />

      <Select
        id="worker-department-id"
        label="所属課"
        {...register("department_id")}
        error={errors.department_id?.message}
        disabled={isSubmitting || isDepartmentsLoading}
        required
      >
        <option value="">
          {isDepartmentsLoading ? "読み込み中..." : "所属課を選択してください"}
        </option>
        {departments.map((dept) => (
          <option key={dept.id} value={dept.id}>
            {dept.name}
          </option>
        ))}
      </Select>

      <Select
        id="worker-skill-rank"
        label="スキルランク"
        {...register("skill_rank_id")}
        error={errors.skill_rank_id?.message}
        disabled={isSubmitting || isSkillRanksLoading}
        required
      >
        <option value="">
          {isSkillRanksLoading ? "読み込み中..." : "スキルランクを選択してください"}
        </option>
        {skillRanks.map((rank) => (
          <option key={rank.id} value={rank.id}>
            {rank.name}
            {rank.is_leader_eligible ? " ★" : ""}
          </option>
        ))}
      </Select>

      <Select
        id="worker-position-id"
        label="役職"
        {...register("position_id")}
        error={errors.position_id?.message}
        disabled={isSubmitting || isPositionsLoading}
      >
        <option value="">
          {isPositionsLoading ? "読み込み中..." : "役職を選択してください（任意）"}
        </option>
        {positions.map((pos) => (
          <option key={pos.id} value={pos.id}>
            {pos.name}
            {pos.is_excluded_from_all_shifts ? " ※除外対象" : ""}
          </option>
        ))}
      </Select>

      <Select
        id="worker-employment-type-id"
        label="雇用形態"
        {...register("employment_type_id")}
        error={errors.employment_type_id?.message}
        disabled={isSubmitting || isEmploymentTypesLoading}
      >
        <option value="">
          {isEmploymentTypesLoading
            ? "読み込み中..."
            : employmentTypes.length === 0
              ? "雇用形態が登録されていません（管理設定から登録できます）"
              : "雇用形態を選択してください（任意）"}
        </option>
        {employmentTypes.map((et) => (
          <option key={et.id} value={et.id}>
            {et.name}
          </option>
        ))}
      </Select>

      <Select
        id="worker-custom-rule-id"
        label="カスタムルール"
        {...register("custom_rule_id")}
        error={errors.custom_rule_id?.message}
        disabled={isSubmitting || isCustomRulesLoading}
      >
        <option value="">
          {isCustomRulesLoading
            ? "読み込み中..."
            : "カスタムルールを選択してください（任意）"}
        </option>
        {customRules.map((rule) => (
          <option key={rule.id} value={rule.id}>
            {rule.name}
          </option>
        ))}
      </Select>

      <Input
        id="worker-birth-date"
        label="生年月日"
        type="date"
        {...register("birth_date")}
        error={errors.birth_date?.message}
        disabled={isSubmitting}
      />

      <Input
        id="worker-skill-acquired-at"
        label="スキルランク取得日"
        type="date"
        {...register("skill_acquired_at")}
        error={errors.skill_acquired_at?.message}
        disabled={isSubmitting}
      />

      <Select
        id="worker-transfer-type"
        label="異動種別"
        {...register("transfer_type")}
        error={errors.transfer_type?.message}
        disabled={isSubmitting}
      >
        {TRANSFER_TYPE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </Select>

      {transferType === "transfer_out" && (
        <Input
          id="worker-transfer-scheduled-month"
          label="異動予定月（YYYY-MM）"
          placeholder="例: 2026-04"
          {...register("transfer_scheduled_month")}
          error={errors.transfer_scheduled_month?.message}
          disabled={isSubmitting}
        />
      )}

      {(transferType === "transfer_in" || transferType === "hired") && (
        <Input
          id="worker-joined-at"
          label="着任日（統計集計の基準日）"
          type="date"
          {...register("joined_at")}
          error={errors.joined_at?.message}
          disabled={isSubmitting}
        />
      )}

      {transferType === "transfer_in" && (
        <div className="flex items-center gap-3">
          <input
            id="worker-is-cross-division-transfer"
            type="checkbox"
            {...register("is_cross_division_transfer")}
            disabled={isSubmitting}
            className="h-4 w-4 rounded border-gray-300 bg-white text-blue-600 focus:ring-blue-500/30"
          />
          <label
            htmlFor="worker-is-cross-division-transfer"
            className="text-sm text-gray-700 cursor-pointer"
          >
            事業本部間異動
          </label>
        </div>
      )}

      <div className="flex justify-end gap-3 mt-2">
        <Button
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          キャンセル
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {isEditing ? "更新する" : "作成する"}
        </Button>
      </div>
    </form>
  );
}

