// frontend/components/aggregate-stats/AggregateStatsTable.tsx
// 集計テーブルコンポーネント（Worker行 × SlotType列）
"use client";

import type {
  AggregateStatsResponse,
  AggregateWorkerSlotStats,
  SlotType,
  WeekdayNightStats,
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

const SLOT_TYPES: SlotType[] = [
  "weekday_night",
  "sat_day",
  "sat_night",
  "sun_hol_day",
  "sun_hol_night",
  "long_hol_day",
  "long_hol_night",
  "sat_pre_hol_night",
];

interface CellProps {
  count: number;
  monthlyAvg: number;
}

function StatCell({ count, monthlyAvg }: CellProps) {
  return (
    <td className="whitespace-nowrap px-3 py-2 text-center text-sm">
      <div className="font-medium text-gray-900">{count}</div>
      <div className="text-xs text-gray-500">{monthlyAvg.toFixed(1)}/月</div>
    </td>
  );
}

interface AggregateStatsTableProps {
  data: AggregateStatsResponse;
}

export function AggregateStatsTable({ data }: AggregateStatsTableProps) {
  const { items } = data;

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          {/* 第1ヘッダー行: SlotType グループ */}
          <tr>
            <th
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-200 px-4 py-2 text-left text-xs font-semibold text-gray-700"
            >
              対応者
            </th>
            <th
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-200 px-3 py-2 text-center text-xs font-semibold text-gray-700"
            >
              有効月数
            </th>
            {/* weekday_night は曜日サブカラムとして結合ヘッダーを表示 */}
            <th
              colSpan={4}
              className="border-b border-r border-gray-200 px-3 py-2 text-center text-xs font-semibold text-blue-700 bg-blue-50"
            >
              {SLOT_TYPE_LABELS.weekday_night}（曜日別）
            </th>
            {/* それ以外の SlotType */}
            {SLOT_TYPES.filter((s) => s !== "weekday_night").map((slot) => (
              <th
                key={slot}
                rowSpan={2}
                className="whitespace-nowrap px-3 py-2 text-center text-xs font-semibold text-gray-700 border-l border-gray-100"
              >
                {SLOT_TYPE_LABELS[slot]}
              </th>
            ))}
          </tr>
          {/* 第2ヘッダー行: 曜日サブカラム */}
          <tr>
            {[0, 1, 2, 3].map((wd) => (
              <th
                key={wd}
                className="whitespace-nowrap border-r border-gray-100 px-3 py-1 text-center text-xs font-medium text-blue-600 bg-blue-50"
              >
                {WEEKDAY_LABELS[wd]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((worker) => {
            const slotMap = new Map<SlotType, AggregateWorkerSlotStats>(
              worker.slot_stats.map((s) => [s.slot_type as SlotType, s]),
            );
            const weekdayNight = slotMap.get("weekday_night");
            const weekdayStatsMap = new Map<number, WeekdayNightStats>(
              (weekdayNight?.weekday_stats ?? []).map((ws) => [ws.weekday, ws]),
            );

            return (
              <tr key={worker.worker_id} className="hover:bg-gray-50">
                <td className="whitespace-nowrap border-r border-gray-200 px-4 py-2 text-sm font-medium text-gray-900">
                  {worker.worker_name}
                </td>
                <td className="whitespace-nowrap border-r border-gray-200 px-3 py-2 text-center text-sm text-gray-600">
                  {worker.effective_months.toFixed(1)}
                </td>
                {/* weekday_night の曜日別カラム */}
                {[0, 1, 2, 3].map((wd) => {
                  const ws = weekdayStatsMap.get(wd);
                  return (
                    <StatCell
                      key={wd}
                      count={ws?.count ?? 0}
                      monthlyAvg={ws?.monthly_avg ?? 0}
                    />
                  );
                })}
                {/* その他の SlotType */}
                {SLOT_TYPES.filter((s) => s !== "weekday_night").map((slot) => {
                  const stats = slotMap.get(slot);
                  return (
                    <StatCell
                      key={slot}
                      count={stats?.count ?? 0}
                      monthlyAvg={stats?.monthly_avg ?? 0}
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
