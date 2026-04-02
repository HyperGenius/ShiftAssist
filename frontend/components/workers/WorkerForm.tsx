"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiSelect } from "@/components/ui/SciFiSelect";
import { useDepartments } from "@/hooks/useDepartments";
import { useSkillRanks } from "@/hooks/useSkillRanks";
import type { Worker, WorkerCreate } from "@/types/worker";

const workerSchema = z.object({
  name: z
    .string()
    .min(1, "氏名は必須です")
    .max(100, "氏名は100文字以内で入力してください"),
  department_id: z.string().uuid("有効な所属課IDを入力してください"),
  skill_rank_id: z.string().uuid("スキルランクを選択してください"),
  is_special: z.boolean(),
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
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<WorkerFormValues>({
    resolver: zodResolver(workerSchema),
    defaultValues: {
      name: worker?.name ?? "",
      department_id: worker?.department_id ?? "",
      skill_rank_id: worker?.skill_rank_id ?? "",
      is_special: worker?.is_special ?? false,
    },
  });

  // worker が切り替わったらフォームをリセット
  useEffect(() => {
    reset({
      name: worker?.name ?? "",
      department_id: worker?.department_id ?? "",
      skill_rank_id: worker?.skill_rank_id ?? "",
      is_special: worker?.is_special ?? false,
    });
  }, [worker, reset]);

  const handleFormSubmit = async (values: WorkerFormValues) => {
    await onSubmit(values);
  };

  const isEditing = !!worker;

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className="flex flex-col gap-4"
    >
      <SciFiInput
        id="worker-name"
        label="氏名"
        placeholder="例: 山田 太郎"
        {...register("name")}
        error={errors.name?.message}
        disabled={isSubmitting}
      />

      <SciFiSelect
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
      </SciFiSelect>

      <SciFiSelect
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
      </SciFiSelect>

      <div className="flex items-center gap-3">
        <input
          id="worker-is-special"
          type="checkbox"
          {...register("is_special")}
          disabled={isSubmitting}
          className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50"
        />
        <label
          htmlFor="worker-is-special"
          className="text-sm text-slate-300 cursor-pointer"
        >
          特別雇用者（平日夜間枠のみアサイン可能）
        </label>
      </div>

      <div className="flex justify-end gap-3 mt-2">
        <SciFiButton
          type="button"
          variant="ghost"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          キャンセル
        </SciFiButton>
        <SciFiButton type="submit" loading={isSubmitting}>
          {isEditing ? "更新する" : "作成する"}
        </SciFiButton>
      </div>
    </form>
  );
}

