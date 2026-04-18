// frontend/components/departments/DepartmentForm.tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { Department, DepartmentCreate } from "@/types/department";

const departmentSchema = z.object({
  name: z
    .string()
    .min(1, "部門名は必須です")
    .max(100, "部門名は100文字以内で入力してください"),
  code: z
    .string()
    .min(1, "部門コードは必須です")
    .max(50, "部門コードは50文字以内で入力してください"),
});

type DepartmentFormValues = z.infer<typeof departmentSchema>;

interface DepartmentFormProps {
  /** 編集対象 Department（新規作成時は undefined）*/
  department?: Department;
  /** フォーム送信ハンドラー */
  onSubmit: (data: DepartmentCreate) => Promise<void>;
  /** キャンセルハンドラー */
  onCancel: () => void;
  /** 送信中フラグ */
  isSubmitting?: boolean;
}

export function DepartmentForm({
  department,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: DepartmentFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DepartmentFormValues>({
    resolver: zodResolver(departmentSchema),
    defaultValues: {
      name: department?.name ?? "",
      code: department?.code ?? "",
    },
  });

  // department が切り替わったらフォームをリセット
  useEffect(() => {
    reset({
      name: department?.name ?? "",
      code: department?.code ?? "",
    });
  }, [department, reset]);

  const handleFormSubmit = async (values: DepartmentFormValues) => {
    await onSubmit(values);
  };

  const isEditing = !!department;

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className="flex flex-col gap-4"
    >
      <Input
        id="department-name"
        label="部門名"
        placeholder="例: 営業部"
        {...register("name")}
        error={errors.name?.message}
        disabled={isSubmitting}
      />

      <Input
        id="department-code"
        label="部門コード"
        placeholder="例: SALES-01"
        {...register("code")}
        error={errors.code?.message}
        disabled={isSubmitting}
      />

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
