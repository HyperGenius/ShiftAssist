// frontend/components/workers/WorkerListFilter.tsx
"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Department } from "@/types/department";
import type { EmploymentType } from "@/types/employmentType";
import type { TenantSkillRank } from "@/types/skillRank";

export interface WorkerFilterState {
  /** 所属課ID（null = 全件） */
  departmentId: string | null;
  /** スキルランクID（null = 全件） */
  skillRankId: string | null;
  /** 雇用形態ID（null = 全件） */
  employmentTypeId: string | null;
  /** 氏名テキスト検索（空文字 = フィルタなし） */
  nameQuery: string;
}

export const INITIAL_FILTER_STATE: WorkerFilterState = {
  departmentId: null,
  skillRankId: null,
  employmentTypeId: null,
  nameQuery: "",
};

export function isFilterActive(state: WorkerFilterState): boolean {
  return (
    state.departmentId !== null ||
    state.skillRankId !== null ||
    state.employmentTypeId !== null ||
    state.nameQuery !== ""
  );
}

interface WorkerListFilterProps {
  departments: Department[];
  skillRanks: TenantSkillRank[];
  employmentTypes: EmploymentType[];
  filterState: WorkerFilterState;
  onChange: (next: WorkerFilterState) => void;
  onReset: () => void;
  filteredCount: number;
  totalCount: number;
}

/** Worker一覧フィルタバー */
export function WorkerListFilter({
  departments,
  skillRanks,
  employmentTypes,
  filterState,
  onChange,
  onReset,
  filteredCount,
  totalCount,
}: WorkerListFilterProps) {
  const active = isFilterActive(filterState);

  return (
    <div
      className={[
        "flex flex-wrap items-end gap-3 p-3 rounded border mb-4",
        active ? "border-blue-300 bg-blue-50" : "border-gray-200 bg-gray-50",
      ].join(" ")}
    >
      {/* 所属課 */}
      <div className="min-w-[140px]">
        <Select
          id="filter-department"
          label="所属課"
          value={filterState.departmentId ?? ""}
          onChange={(e) =>
            onChange({
              ...filterState,
              departmentId: e.target.value === "" ? null : e.target.value,
            })
          }
        >
          <option value="">すべて</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
      </div>

      {/* スキルランク */}
      <div className="min-w-[140px]">
        <Select
          id="filter-skill-rank"
          label="スキルランク"
          value={filterState.skillRankId ?? ""}
          onChange={(e) =>
            onChange({
              ...filterState,
              skillRankId: e.target.value === "" ? null : e.target.value,
            })
          }
        >
          <option value="">すべて</option>
          {skillRanks.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </Select>
      </div>

      {/* 雇用形態 */}
      <div className="min-w-[140px]">
        <Select
          id="filter-employment-type"
          label="雇用形態"
          value={filterState.employmentTypeId ?? ""}
          onChange={(e) =>
            onChange({
              ...filterState,
              employmentTypeId: e.target.value === "" ? null : e.target.value,
            })
          }
        >
          <option value="">すべて</option>
          {employmentTypes.map((et) => (
            <option key={et.id} value={et.id}>
              {et.name}
            </option>
          ))}
        </Select>
      </div>

      {/* 氏名検索 */}
      <div className="min-w-[160px] flex-1">
        <Input
          id="filter-name"
          label="氏名"
          placeholder="氏名で絞り込み"
          value={filterState.nameQuery}
          onChange={(e) =>
            onChange({ ...filterState, nameQuery: e.target.value })
          }
        />
      </div>

      {/* クリア & 件数 */}
      <div className="flex items-center gap-2 pb-0.5">
        {active && (
          <>
            <span className="text-xs text-blue-600 font-medium whitespace-nowrap">
              {filteredCount}/{totalCount} 件
            </span>
            <Button variant="ghost" size="sm" onClick={onReset}>
              クリア
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
