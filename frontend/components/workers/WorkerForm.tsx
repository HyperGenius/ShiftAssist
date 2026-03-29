// frontend/components/workers/WorkerForm.tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiInput } from "@/components/ui/SciFiInput";
import { SciFiSelect } from "@/components/ui/SciFiSelect";
import type { Worker, WorkerCreate } from "@/types/worker";

const workerSchema = z.object({
  name: z
    .string()
    .min(1, "氏名は必須です")
    .max(100, "氏名は100文字以内で入力してください"),
  department_id: z.string().uuid("有効な所属課IDを入力してください"),
  skill_rank: z.enum(["rank_a", "rank_b", "rank_c", "rank_d"] as const, {
    error: "スキルランクを選択してください",
  }),
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
      skill_rank: worker?.skill_rank ?? "rank_a",
      is_special: worker?.is_special ?? false,
    },
  });

  // worker が切り替わったらフォームをリセット
  useEffect(() => {
    reset({
      name: worker?.name ?? "",
      department_id: worker?.department_id ?? "",
      skill_rank: worker?.skill_rank ?? "rank_a",
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

      <SciFiInput
        id="worker-department-id"
        label="所属課 ID (UUID)"
        placeholder="例: 550e8400-e29b-41d4-a716-446655440000"
        {...register("department_id")}
        error={errors.department_id?.message}
        disabled={isSubmitting}
      />

      <SciFiSelect
        id="worker-skill-rank"
        label="スキルランク"
        {...register("skill_rank")}
        error={errors.skill_rank?.message}
        disabled={isSubmitting}
      >
        <option value="rank_a">ランク A</option>
        <option value="rank_b">ランク B</option>
        <option value="rank_c">ランク C</option>
        <option value="rank_d">ランク D</option>
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
