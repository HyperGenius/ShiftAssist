"use client";

import type { Department } from "@/types/department";
import type { Position } from "@/types/position";

export interface WorkerFilterState {
  departmentId: string | null;
  positionId: string | null;
  nameQuery: string;
}

interface WorkerFilterBarProps {
  departments: Department[];
  positions: Position[];
  filterState: WorkerFilterState;
  onChange: (next: WorkerFilterState) => void;
  onReset: () => void;
  /** フィルタ後の件数 */
  filteredCount: number;
  /** フィルタ前の総件数 */
  totalCount: number;
}

/** フィルタが1つ以上適用されているか */
function isAnyFilterActive(state: WorkerFilterState): boolean {
  return (
    state.departmentId !== null ||
    state.positionId !== null ||
    state.nameQuery !== ""
  );
}

/**
 * 対応者リストパネルのフィルタUIコンポーネント。
 * 所属課・役職プルダウンと氏名テキスト入力を提供する。
 */
export function WorkerFilterBar({
  departments,
  positions,
  filterState,
  onChange,
  onReset,
  filteredCount,
  totalCount,
}: WorkerFilterBarProps) {
  const isActive = isAnyFilterActive(filterState);

  const selectBase =
    "w-full text-[12px] rounded border py-1 px-1 bg-white leading-tight focus:outline-none focus:ring-1 focus:ring-blue-400";
  const selectNormal = `${selectBase} border-gray-200 text-gray-600`;
  const selectActive = `${selectBase} border-blue-300 text-blue-700 bg-blue-50`;

  return (
    <div className="mt-1.5 space-y-1">
      {/* 所属課プルダウン */}
      <select
        value={filterState.departmentId ?? ""}
        onChange={(e) =>
          onChange({
            ...filterState,
            departmentId: e.target.value === "" ? null : e.target.value,
          })
        }
        className={filterState.departmentId !== null ? selectActive : selectNormal}
        aria-label="所属課で絞り込む"
      >
        <option value="">全所属課</option>
        {departments.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name}
          </option>
        ))}
      </select>

      {/* 役職プルダウン */}
      <select
        value={filterState.positionId ?? ""}
        onChange={(e) =>
          onChange({
            ...filterState,
            positionId: e.target.value === "" ? null : e.target.value,
          })
        }
        className={filterState.positionId !== null ? selectActive : selectNormal}
        aria-label="役職で絞り込む"
      >
        <option value="">全役職</option>
        {positions.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      {/* 氏名テキスト入力 */}
      <div className="relative">
        <input
          type="text"
          value={filterState.nameQuery}
          onChange={(e) =>
            onChange({ ...filterState, nameQuery: e.target.value })
          }
          placeholder="氏名で絞り込む"
          className={[
            "w-full text-[13px] rounded border py-1 pl-2 pr-5 bg-white leading-tight focus:outline-none focus:ring-1 focus:ring-blue-400",
            filterState.nameQuery !== ""
              ? "border-blue-300 bg-blue-50 text-blue-700"
              : "border-gray-200 text-gray-600",
          ].join(" ")}
          aria-label="氏名で絞り込む"
        />
        {filterState.nameQuery !== "" && (
          <button
            type="button"
            onClick={() => onChange({ ...filterState, nameQuery: "" })}
            className="absolute right-0.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 px-1 text-[13px] leading-none"
            aria-label="氏名フィルタをクリア"
          >
            ×
          </button>
        )}
      </div>

      {/* フィルタ状態行: カウント + リセットボタン */}
      {isActive && (
        <div className="flex items-center justify-between pt-0.5">
          <span className="text-[10px] text-blue-600 font-medium">
            {filteredCount}/{totalCount}
          </span>
          <button
            type="button"
            onClick={onReset}
            className="text-[10px] text-gray-500 hover:text-gray-700 underline"
          >
            フィルタをリセット
          </button>
        </div>
      )}
    </div>
  );
}
