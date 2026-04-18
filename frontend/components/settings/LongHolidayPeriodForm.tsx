// frontend/components/settings/LongHolidayPeriodForm.tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type {
  LongHolidayPeriodCreate,
  LongHolidayType,
} from "@/types/longHolidayPeriod";

export const HOLIDAY_TYPE_LABELS: Record<LongHolidayType, string> = {
  gw: "ゴールデンウィーク",
  sw: "シルバーウィーク",
  year_end: "年末年始",
};

const HOLIDAY_TYPES: LongHolidayType[] = ["gw", "sw", "year_end"];

interface LongHolidayPeriodFormProps {
  defaultYear?: number;
  onSubmit: (payload: LongHolidayPeriodCreate) => Promise<void>;
}

/** 長期休暇期間の新規追加フォーム */
export function LongHolidayPeriodForm({
  defaultYear,
  onSubmit,
}: LongHolidayPeriodFormProps) {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState<string>(
    String(defaultYear ?? currentYear),
  );
  const [holidayType, setHolidayType] = useState<LongHolidayType>("gw");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dateError, setDateError] = useState("");

  const validate = (): boolean => {
    if (startDate && endDate && startDate > endDate) {
      setDateError("開始日は終了日以前の日付を指定してください");
      return false;
    }
    setDateError("");
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setIsSubmitting(true);
    try {
      await onSubmit({
        year: Number(year),
        holiday_type: holidayType,
        start_date: startDate,
        end_date: endDate,
      });
      setStartDate("");
      setEndDate("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Input
          id="lhp-year"
          label="年"
          type="number"
          min={2000}
          max={2100}
          required
          value={year}
          onChange={(e) => setYear(e.target.value)}
        />
        <Select
          id="lhp-type"
          label="休暇種別"
          value={holidayType}
          onChange={(e) => setHolidayType(e.target.value as LongHolidayType)}
        >
          {HOLIDAY_TYPES.map((t) => (
            <option key={t} value={t}>
              {HOLIDAY_TYPE_LABELS[t]}
            </option>
          ))}
        </Select>
        <Input
          id="lhp-start"
          label="開始日"
          type="date"
          required
          value={startDate}
          onChange={(e) => {
            setStartDate(e.target.value);
            setDateError("");
          }}
          error={
            dateError && startDate && endDate ? dateError : undefined
          }
        />
        <Input
          id="lhp-end"
          label="終了日"
          type="date"
          required
          value={endDate}
          onChange={(e) => {
            setEndDate(e.target.value);
            setDateError("");
          }}
          error={
            dateError && startDate && endDate ? dateError : undefined
          }
        />
      </div>
      <div className="flex justify-end">
        <Button type="submit" size="sm" loading={isSubmitting}>
          追加する
        </Button>
      </div>
    </form>
  );
}
