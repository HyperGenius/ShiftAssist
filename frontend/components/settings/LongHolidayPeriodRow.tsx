// frontend/components/settings/LongHolidayPeriodRow.tsx
"use client";

import { useState } from "react";

import { SciFiButton } from "@/components/ui/SciFiButton";
import { SciFiInput } from "@/components/ui/SciFiInput";
import type {
  LongHolidayPeriod,
  LongHolidayPeriodUpdate,
} from "@/types/longHolidayPeriod";

import { HOLIDAY_TYPE_LABELS } from "./LongHolidayPeriodForm";

interface LongHolidayPeriodRowProps {
  period: LongHolidayPeriod;
  onUpdate: (id: string, payload: LongHolidayPeriodUpdate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

/** 長期休暇期間の一行表示・インライン編集・削除コンポーネント */
export function LongHolidayPeriodRow({
  period,
  onUpdate,
  onDelete,
}: LongHolidayPeriodRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [startDate, setStartDate] = useState(period.start_date);
  const [endDate, setEndDate] = useState(period.end_date);
  const [dateError, setDateError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = async () => {
    if (startDate > endDate) {
      setDateError("開始日は終了日以前の日付を指定してください");
      return;
    }
    setDateError("");
    setIsSaving(true);
    try {
      await onUpdate(period.id, { start_date: startDate, end_date: endDate });
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(period.id);
    } finally {
      setIsDeleting(false);
      setConfirmDelete(false);
    }
  };

  const handleCancelEdit = () => {
    setStartDate(period.start_date);
    setEndDate(period.end_date);
    setDateError("");
    setIsEditing(false);
  };

  return (
    <div className="flex flex-col gap-2 rounded border border-gray-200 bg-white p-3 sm:flex-row sm:items-center sm:gap-4">
      <div className="flex-1 min-w-0">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          {HOLIDAY_TYPE_LABELS[period.holiday_type]}
        </span>
        <span className="ml-2 text-xs text-gray-400">{period.year}年</span>
      </div>

      {isEditing ? (
        <div className="flex flex-wrap items-end gap-2 flex-1">
          <SciFiInput
            id={`start-${period.id}`}
            label="開始日"
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setDateError("");
            }}
          />
          <SciFiInput
            id={`end-${period.id}`}
            label="終了日"
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setDateError("");
            }}
            error={dateError || undefined}
          />
          <div className="flex gap-2 items-end pb-0.5">
            <SciFiButton
              size="sm"
              onClick={() => void handleSave()}
              loading={isSaving}
            >
              保存
            </SciFiButton>
            <SciFiButton
              size="sm"
              variant="secondary"
              onClick={handleCancelEdit}
              disabled={isSaving}
            >
              キャンセル
            </SciFiButton>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-4 flex-1">
          <span className="text-sm text-gray-700">
            {period.start_date} 〜 {period.end_date}
          </span>
          <div className="flex gap-2 ml-auto">
            <SciFiButton
              size="sm"
              variant="secondary"
              onClick={() => setIsEditing(true)}
            >
              編集
            </SciFiButton>
            {confirmDelete ? (
              <>
                <SciFiButton
                  size="sm"
                  variant="danger"
                  onClick={() => void handleDelete()}
                  loading={isDeleting}
                >
                  削除確定
                </SciFiButton>
                <SciFiButton
                  size="sm"
                  variant="ghost"
                  onClick={() => setConfirmDelete(false)}
                  disabled={isDeleting}
                >
                  キャンセル
                </SciFiButton>
              </>
            ) : (
              <SciFiButton
                size="sm"
                variant="danger"
                onClick={() => setConfirmDelete(true)}
              >
                削除
              </SciFiButton>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
