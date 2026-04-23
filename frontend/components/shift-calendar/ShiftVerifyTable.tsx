// frontend/components/shift-calendar/ShiftVerifyTable.tsx
// Verify機能用テーブルコンポーネント（Worker行 × SlotType列、Before/After/Δ 表示）
"use client";

import type {
  ShiftVerifyResponse,
  ShiftVerifySlotStat,
  ShiftVerifyWeekdayDelta,
  SlotType,
} from "@/types/workerStats";

/** SlotType の表示名マップ */
const SLOT_TYPE_LABELS: Record<SlotType, string> = {
  weekday_night: "平日夜",
  sat_day: "土昼",
  sat_night: "土夜",
  sun_hol_day: "日祝昼",
  sun_hol_night: "日祝夜",
  long_hol_day: "連休昼",
  long_hol_night: "連休夜",
  sat_pre_hol_night: "祝前夜",
};

/** weekday_night の曜日表示名 */
const WEEKDAY_LABELS: Record<number, string> = {
  0: "月",
  1: "火",
  2: "水",
  3: "木",
};

const SLOT_TYPES_WITHOUT_WEEKDAY: SlotType[] = [
  "sat_day",
  "sat_night",
  "sun_hol_day",
  "sun_hol_night",
  "long_hol_day",
  "long_hol_night",
];

interface VerifyCellProps {
  beforeAvg: number;
  afterAvg: number;
  deltaCount: number;
  isOutlier: boolean;
}

/** Before / After / Δ を縦積みで表示するセル */
function VerifyCell({ beforeAvg, afterAvg, deltaCount, isOutlier }: VerifyCellProps) {
  const deltaSign = deltaCount > 0 ? "+" : deltaCount < 0 ? "" : "±";
  const deltaColor =
    deltaCount > 0
      ? "text-orange-600"
      : deltaCount < 0
        ? "text-blue-600"
        : "text-gray-400";

  return (
    <td
      className={`whitespace-nowrap px-2 py-1 text-center text-xs align-middle ${
        isOutlier ? "bg-amber-50" : ""
      }`}
      aria-label={`Before ${beforeAvg.toFixed(1)}/月 After ${afterAvg.toFixed(1)}/月 差分 ${deltaSign}${deltaCount}${isOutlier ? " 突出" : ""}`}
    >
      {isOutlier && (
        <div className="text-[9px] font-bold text-amber-600 leading-none mb-0.5" aria-hidden="true">⚠</div>
      )}
      <div className="text-gray-400 leading-tight" aria-hidden="true">{beforeAvg.toFixed(1)}</div>
      <div className={`font-semibold leading-tight ${isOutlier ? "text-amber-700" : "text-gray-900"}`} aria-hidden="true">
        {afterAvg.toFixed(1)}
      </div>
      <div className={`text-[10px] leading-tight ${deltaColor}`} aria-hidden="true">
        {deltaSign}{deltaCount}
      </div>
    </td>
  );
}

interface ShiftVerifyTableProps {
  data: ShiftVerifyResponse;
}

export function ShiftVerifyTable({ data }: ShiftVerifyTableProps) {
  const { items, before_period, after_period } = data;

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-400 text-sm">
        集計対象のワーカーが見つかりません。
      </div>
    );
  }

  return (
    <div className="overflow-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* 凡例 */}
      <div className="flex items-center gap-4 px-3 py-2 border-b border-gray-100 text-xs text-gray-500">
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-gray-300 mr-1" />
          Before 月平均（{before_period}）
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded-full bg-gray-700 mr-1" />
          After 月平均（{after_period}）
        </span>
        <span>
          <span className="text-orange-600 mr-1">+N</span>差分（Delta）
        </span>
        <span>
          <span className="inline-block w-2 h-2 rounded bg-amber-100 border border-amber-300 mr-1" />
          ⚠ 突出（After 月平均 {">"} 平均 + 標準偏差）
        </span>
      </div>
      <table className="min-w-full divide-y divide-gray-200 text-xs">
        <thead className="bg-gray-50 sticky top-0 z-20">
          {/* 第1ヘッダー行 */}
          <tr>
            <th
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-700 sticky left-0 z-30 bg-gray-50"
            >
              対応者名
            </th>
            <th
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-200 px-2 py-2 text-left text-xs font-semibold text-gray-700"
            >
              所属課
            </th>
            <th
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-200 px-2 py-2 text-center text-xs font-semibold text-gray-700"
            >
              有効月数
            </th>
            {/* 平日夜（曜日別グループ） */}
            <th
              colSpan={4}
              className="border-b border-r border-gray-200 px-2 py-1 text-center text-xs font-semibold text-blue-700 bg-blue-50"
            >
              {SLOT_TYPE_LABELS.weekday_night}（曜日別）
            </th>
            {/* 祝前夜 */}
            <th
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-100 px-2 py-2 text-center text-xs font-semibold text-gray-700"
            >
              {SLOT_TYPE_LABELS.sat_pre_hol_night}
            </th>
            {/* 土曜日グループ */}
            <th
              colSpan={2}
              className="border-b border-l border-r border-gray-200 px-2 py-1 text-center text-xs font-semibold text-gray-700"
            >
              土曜日
            </th>
            {/* 日祝グループ */}
            <th
              colSpan={2}
              className="border-b border-l border-r border-gray-200 px-2 py-1 text-center text-xs font-semibold text-gray-700"
            >
              日祝
            </th>
            {/* 連休グループ */}
            <th
              colSpan={2}
              className="border-b border-l border-gray-200 px-2 py-1 text-center text-xs font-semibold text-gray-700"
            >
              連休
            </th>
          </tr>
          {/* 第2ヘッダー行 */}
          <tr>
            {/* 平日夜曜日サブカラム */}
            {[0, 1, 2, 3].map((wd) => (
              <th
                key={wd}
                className="whitespace-nowrap border-r border-gray-100 px-2 py-1 text-center text-xs font-medium text-blue-600 bg-blue-50"
              >
                {WEEKDAY_LABELS[wd]}
              </th>
            ))}
            {/* 土昼・土夜 */}
            <th className="whitespace-nowrap border-l border-gray-100 px-2 py-1 text-center text-xs font-medium text-gray-600">
              昼
            </th>
            <th className="whitespace-nowrap border-r border-gray-100 px-2 py-1 text-center text-xs font-medium text-gray-600">
              夜
            </th>
            {/* 日祝昼・日祝夜 */}
            <th className="whitespace-nowrap border-l border-gray-100 px-2 py-1 text-center text-xs font-medium text-gray-600">
              昼
            </th>
            <th className="whitespace-nowrap border-r border-gray-100 px-2 py-1 text-center text-xs font-medium text-gray-600">
              夜
            </th>
            {/* 連休昼・連休夜 */}
            <th className="whitespace-nowrap border-l border-gray-100 px-2 py-1 text-center text-xs font-medium text-gray-600">
              昼
            </th>
            <th className="whitespace-nowrap px-2 py-1 text-center text-xs font-medium text-gray-600">
              夜
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((worker) => {
            const slotMap = new Map<SlotType, ShiftVerifySlotStat>(
              worker.slot_stats.map((s) => [s.slot_type as SlotType, s]),
            );
            const weekdayNight = slotMap.get("weekday_night");
            const weekdayDeltaMap = new Map<number, ShiftVerifyWeekdayDelta>(
              (weekdayNight?.weekday_stats ?? []).map((ws) => [ws.weekday, ws]),
            );

            return (
              <tr key={worker.worker_id} className="hover:bg-gray-50">
                {/* 対応者名 */}
                <td className="whitespace-nowrap border-r border-gray-200 px-3 py-1 text-xs font-medium text-gray-900 sticky left-0 z-10 bg-white">
                  {worker.worker_name}
                </td>
                {/* 所属課 */}
                <td className="whitespace-nowrap border-r border-gray-200 px-2 py-1 text-xs text-gray-600">
                  {worker.department_name ?? "—"}
                </td>
                {/* 有効月数 */}
                <td className="whitespace-nowrap border-r border-gray-200 px-2 py-1 text-center text-xs text-gray-600">
                  {worker.effective_months.toFixed(1)}
                </td>
                {/* 平日夜 曜日別カラム */}
                {[0, 1, 2, 3].map((wd) => {
                  const ws = weekdayDeltaMap.get(wd);
                  return (
                    <VerifyCell
                      key={wd}
                      beforeAvg={ws?.before_monthly_avg ?? 0}
                      afterAvg={ws?.after_monthly_avg ?? 0}
                      deltaCount={ws?.delta_count ?? 0}
                      isOutlier={false}
                    />
                  );
                })}
                {/* 祝前夜 */}
                {(() => {
                  const s = slotMap.get("sat_pre_hol_night");
                  return (
                    <VerifyCell
                      beforeAvg={s?.before_monthly_avg ?? 0}
                      afterAvg={s?.after_monthly_avg ?? 0}
                      deltaCount={s?.delta_count ?? 0}
                      isOutlier={s?.is_outlier ?? false}
                    />
                  );
                })()}
                {/* 土昼・土夜・日祝昼・日祝夜・連休昼・連休夜 */}
                {SLOT_TYPES_WITHOUT_WEEKDAY.map((slot) => {
                  const s = slotMap.get(slot);
                  return (
                    <VerifyCell
                      key={slot}
                      beforeAvg={s?.before_monthly_avg ?? 0}
                      afterAvg={s?.after_monthly_avg ?? 0}
                      deltaCount={s?.delta_count ?? 0}
                      isOutlier={s?.is_outlier ?? false}
                    />
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
