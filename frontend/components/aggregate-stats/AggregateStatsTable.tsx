// frontend/components/aggregate-stats/AggregateStatsTable.tsx
// 集計テーブルコンポーネント（Worker行 × SlotType列）
"use client";

import { useMemo, useState } from "react";

import { EmploymentTypeBadge, InfoBadge } from "@/components/ui/WorkerAttributeBadge";
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

const SLOT_TYPES_WITHOUT_WEEKDAY: SlotType[] = [
  "sat_day",
  "sat_night",
  "sun_hol_day",
  "sun_hol_night",
  "long_hol_day",
  "long_hol_night",
];

/** 左固定列のオフセット位置（px）。列幅が変わった場合はここだけ修正する。 */
const STICKY_LEFT = {
  workerName: "left-0",
  position: "left-[120px]",
  department: "left-[200px]",
  skillRank: "left-[300px]",
} as const;

// ソート可能なカラムキー
type SortKey =
  | "worker_name"
  | "position_name"
  | "department_name"
  | "skill_rank_name"
  | "effective_months"
  | SlotType;

type SortDir = "asc" | "desc";

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

/** ソートアイコン表示 */
function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="ml-1 text-gray-300 text-[10px]">▲▼</span>;
  return (
    <span className="ml-1 text-blue-600 text-[10px]">{dir === "asc" ? "▲" : "▼"}</span>
  );
}

/** ソート可能なヘッダーセル */
function SortableHeader({
  children,
  sortKey,
  currentSort,
  onSort,
  className,
  ...rest
}: {
  children: React.ReactNode;
  sortKey: SortKey;
  currentSort: { key: SortKey; dir: SortDir };
  onSort: (key: SortKey) => void;
  className?: string;
} & React.ThHTMLAttributes<HTMLTableCellElement>) {
  const isActive = currentSort.key === sortKey;
  return (
    <th
      {...rest}
      className={`cursor-pointer select-none hover:bg-gray-100 transition-colors ${className ?? ""}`}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center">
        {children}
        <SortIcon active={isActive} dir={currentSort.dir} />
      </span>
    </th>
  );
}

/** 有効月数を計算する（joined_at または skill_acquired_at から現在までの月数） */
function computeEffectiveMonthsFromDate(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const start = new Date(dateStr);
  const now = new Date();
  const months =
    (now.getFullYear() - start.getFullYear()) * 12 +
    (now.getMonth() - start.getMonth());
  return months;
}

interface AggregateStatsTableProps {
  data: AggregateStatsResponse;
}

export function AggregateStatsTable({ data }: AggregateStatsTableProps) {
  const { items } = data;

  const [sortKey, setSortKey] = useState<SortKey>("department_name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      let aVal: string | number | null = null;
      let bVal: string | number | null = null;

      if (
        sortKey === "worker_name" ||
        sortKey === "position_name" ||
        sortKey === "department_name" ||
        sortKey === "skill_rank_name"
      ) {
        aVal = (a[sortKey] ?? "") as string;
        bVal = (b[sortKey] ?? "") as string;
      } else if (sortKey === "effective_months") {
        aVal = a.effective_months;
        bVal = b.effective_months;
      } else {
        // SlotType カラムのソート: 合計回数で比較
        const slotKey = sortKey as SlotType;
        const aStats = a.slot_stats.find((s) => s.slot_type === slotKey);
        const bStats = b.slot_stats.find((s) => s.slot_type === slotKey);
        aVal = aStats?.count ?? 0;
        bVal = bStats?.count ?? 0;
      }

      if (aVal === null || aVal === undefined) aVal = "";
      if (bVal === null || bVal === undefined) bVal = "";

      let cmp = 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        cmp = aVal.localeCompare(bVal, "ja");
      } else {
        cmp = (aVal as number) - (bVal as number);
      }

      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [items, sortKey, sortDir]);

  if (items.length === 0) {
    return null;
  }

  const currentSort = { key: sortKey, dir: sortDir };

  return (
    <div className="max-h-[70vh] overflow-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 sticky top-0 z-20">
          {/* 第1ヘッダー行: 属性グループ＋SlotType グループ */}
          <tr>
            {/* 対応者名（2行分） */}
            <SortableHeader
              sortKey="worker_name"
              currentSort={currentSort}
              onSort={handleSort}
              rowSpan={2}
              className={`whitespace-nowrap border-r border-gray-200 px-4 py-2 text-left text-xs font-semibold text-gray-700 sticky ${STICKY_LEFT.workerName} z-30 bg-gray-50`}
            >
              対応者名
            </SortableHeader>
            {/* 役職（2行分） */}
            <SortableHeader
              sortKey="position_name"
              currentSort={currentSort}
              onSort={handleSort}
              rowSpan={2}
              className={`whitespace-nowrap border-r border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-700 sticky ${STICKY_LEFT.position} z-30 bg-gray-50`}
            >
              役職
            </SortableHeader>
            {/* 所属課名（2行分） */}
            <SortableHeader
              sortKey="department_name"
              currentSort={currentSort}
              onSort={handleSort}
              rowSpan={2}
              className={`whitespace-nowrap border-r border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-700 sticky ${STICKY_LEFT.department} z-30 bg-gray-50`}
            >
              所属課
            </SortableHeader>
            {/* スキルランク（2行分） */}
            <SortableHeader
              sortKey="skill_rank_name"
              currentSort={currentSort}
              onSort={handleSort}
              rowSpan={2}
              className={`whitespace-nowrap border-r border-gray-200 px-3 py-2 text-left text-xs font-semibold text-gray-700 sticky ${STICKY_LEFT.skillRank} z-30 bg-gray-50`}
            >
              スキル
            </SortableHeader>
            {/* 有効月数（2行分） */}
            <SortableHeader
              sortKey="effective_months"
              currentSort={currentSort}
              onSort={handleSort}
              rowSpan={2}
              className="whitespace-nowrap border-r border-gray-200 px-3 py-2 text-center text-xs font-semibold text-gray-700"
            >
              有効月数
            </SortableHeader>
            {/* 平日夜（曜日別グループ） */}
            <th
              colSpan={4}
              className="border-b border-r border-gray-200 px-3 py-2 text-center text-xs font-semibold text-blue-700 bg-blue-50"
            >
              {SLOT_TYPE_LABELS.weekday_night}（曜日別）
            </th>
            {/* 祝前夜 */}
            <SortableHeader
              sortKey="sat_pre_hol_night"
              currentSort={currentSort}
              onSort={handleSort}
              rowSpan={2}
              className="whitespace-nowrap px-3 py-2 text-center text-xs font-semibold text-gray-700 border-l border-gray-100"
            >
              {SLOT_TYPE_LABELS.sat_pre_hol_night}
            </SortableHeader>
            {/* 土曜日グループ */}
            <th
              colSpan={2}
              className="border-b border-l border-r border-gray-200 px-3 py-2 text-center text-xs font-semibold text-gray-700"
            >
              土曜日
            </th>
            {/* 日祝グループ */}
            <th
              colSpan={2}
              className="border-b border-l border-r border-gray-200 px-3 py-2 text-center text-xs font-semibold text-gray-700"
            >
              日祝
            </th>
            {/* 連休グループ */}
            <th
              colSpan={2}
              className="border-b border-l border-gray-200 px-3 py-2 text-center text-xs font-semibold text-gray-700"
            >
              連休
            </th>
          </tr>
          {/* 第2ヘッダー行: 曜日サブカラム＋各SlotType詳細 */}
          <tr>
            {/* 平日夜曜日サブカラム */}
            {[0, 1, 2, 3].map((wd) => (
              <th
                key={wd}
                className="whitespace-nowrap border-r border-gray-100 px-3 py-1 text-center text-xs font-medium text-blue-600 bg-blue-50"
              >
                {WEEKDAY_LABELS[wd]}
              </th>
            ))}
            {/* 土昼・土夜 */}
            <SortableHeader
              sortKey="sat_day"
              currentSort={currentSort}
              onSort={handleSort}
              className="whitespace-nowrap border-l border-gray-100 px-3 py-1 text-center text-xs font-medium text-gray-600"
            >
              昼
            </SortableHeader>
            <SortableHeader
              sortKey="sat_night"
              currentSort={currentSort}
              onSort={handleSort}
              className="whitespace-nowrap border-r border-gray-100 px-3 py-1 text-center text-xs font-medium text-gray-600"
            >
              夜
            </SortableHeader>
            {/* 日祝昼・日祝夜 */}
            <SortableHeader
              sortKey="sun_hol_day"
              currentSort={currentSort}
              onSort={handleSort}
              className="whitespace-nowrap border-l border-gray-100 px-3 py-1 text-center text-xs font-medium text-gray-600"
            >
              昼
            </SortableHeader>
            <SortableHeader
              sortKey="sun_hol_night"
              currentSort={currentSort}
              onSort={handleSort}
              className="whitespace-nowrap border-r border-gray-100 px-3 py-1 text-center text-xs font-medium text-gray-600"
            >
              夜
            </SortableHeader>
            {/* 連休昼・連休夜 */}
            <SortableHeader
              sortKey="long_hol_day"
              currentSort={currentSort}
              onSort={handleSort}
              className="whitespace-nowrap border-l border-gray-100 px-3 py-1 text-center text-xs font-medium text-gray-600"
            >
              昼
            </SortableHeader>
            <SortableHeader
              sortKey="long_hol_night"
              currentSort={currentSort}
              onSort={handleSort}
              className="whitespace-nowrap px-3 py-1 text-center text-xs font-medium text-gray-600"
            >
              夜
            </SortableHeader>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sortedItems.map((worker) => {
            const slotMap = new Map<SlotType, AggregateWorkerSlotStats>(
              worker.slot_stats.map((s) => [s.slot_type as SlotType, s]),
            );
            const weekdayNight = slotMap.get("weekday_night");
            const weekdayStatsMap = new Map<number, WeekdayNightStats>(
              (weekdayNight?.weekday_stats ?? []).map((ws) => [ws.weekday, ws]),
            );

            // 有効月数バッジ判定（joined_at または skill_acquired_at から計算）
            const joinedMonths = computeEffectiveMonthsFromDate(worker.joined_at);
            const skillMonths = computeEffectiveMonthsFromDate(worker.skill_acquired_at);
            const minMonths =
              joinedMonths !== null && skillMonths !== null
                ? Math.min(joinedMonths, skillMonths)
                : joinedMonths ?? skillMonths;
            const showInfoBadge = minMonths !== null && minMonths < 12;
            const infoBadgeTooltip =
              joinedMonths !== null
                ? `有効月数: ${joinedMonths}ヶ月`
                : skillMonths !== null
                  ? `スキル取得: ${skillMonths}ヶ月`
                  : "";

            return (
              <tr key={worker.worker_id} className="hover:bg-gray-50">
                {/* 対応者名 */}
                <td className={`whitespace-nowrap border-r border-gray-200 px-4 py-2 text-sm font-medium text-gray-900 sticky ${STICKY_LEFT.workerName} z-10 bg-white`}>
                  <span className="inline-flex items-center">
                    {worker.worker_name}
                    {showInfoBadge && <InfoBadge tooltip={infoBadgeTooltip} />}
                    {worker.is_non_default_employment && worker.employment_type_name && (
                      <EmploymentTypeBadge
                        label={worker.employment_type_name}
                        tooltip={worker.employment_type_name}
                      />
                    )}
                  </span>
                </td>
                {/* 役職 */}
                <td className={`whitespace-nowrap border-r border-gray-200 px-3 py-2 text-sm text-gray-600 sticky ${STICKY_LEFT.position} z-10 bg-white`}>
                  {worker.position_name ?? "—"}
                </td>
                {/* 所属課 */}
                <td className={`whitespace-nowrap border-r border-gray-200 px-3 py-2 text-sm text-gray-600 sticky ${STICKY_LEFT.department} z-10 bg-white`}>
                  {worker.department_name ?? "—"}
                </td>
                {/* スキルランク */}
                <td className={`whitespace-nowrap border-r border-gray-200 px-3 py-2 text-sm text-gray-600 sticky ${STICKY_LEFT.skillRank} z-10 bg-white`}>
                  {worker.skill_rank_name ?? "—"}
                </td>
                {/* 有効月数 */}
                <td className="whitespace-nowrap border-r border-gray-200 px-3 py-2 text-center text-sm text-gray-600">
                  {worker.effective_months.toFixed(1)}
                </td>
                {/* 平日夜 曜日別カラム */}
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
                {/* 祝前夜 */}
                {(() => {
                  const s = slotMap.get("sat_pre_hol_night");
                  return <StatCell count={s?.count ?? 0} monthlyAvg={s?.monthly_avg ?? 0} />;
                })()}
                {/* 土昼・土夜・日祝昼・日祝夜・連休昼・連休夜 */}
                {SLOT_TYPES_WITHOUT_WEEKDAY.map(
                  (slot) => {
                    const s = slotMap.get(slot);
                    return (
                      <StatCell
                        key={slot}
                        count={s?.count ?? 0}
                        monthlyAvg={s?.monthly_avg ?? 0}
                      />
                    );
                  },
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
