# 対応者フィルタ機能 (Worker Filter Feature)

## 概要

本機能は2箇所に実装されています。

1. **シフト枠カレンダーの対応者リストパネル** (`WorkerListPanel`): 所属課・役職・個人名でフィルタリング
2. **Worker管理ページ** (`/admin/settings/workers`): 所属課・スキルランク・雇用形態・氏名でフィルタリング

いずれもフィルタ処理はフロントエンドのみで完結し、バックエンドへの追加APIコールは発生しません。

---

## 実装コンポーネント

### `frontend/utils/stringUtils.ts`

文字列正規化ユーティリティ。

| 関数 | 説明 |
|------|------|
| `normalizeForSearch(str)` | NFKC正規化（全角→半角）＋小文字化で検索用に正規化する |
| `matchesNormalized(text, query)` | `query` が空の場合は常に `true`。正規化した上で部分一致を判定する |

### `frontend/components/shift-calendar/WorkerFilterBar.tsx`

シフトカレンダーの対応者リスト用フィルタUIコンポーネント。

#### Props

| Prop | 型 | 説明 |
|------|----|------|
| `departments` | `Department[]` | 所属課リスト（プルダウン選択肢生成に使用） |
| `positions` | `Position[]` | 役職リスト（プルダウン選択肢生成に使用） |
| `filterState` | `WorkerFilterState` | 現在のフィルタ状態 |
| `onChange` | `(next: WorkerFilterState) => void` | フィルタ変更コールバック |
| `onReset` | `() => void` | 全フィルタリセットコールバック |
| `filteredCount` | `number` | フィルタ後の件数 |
| `totalCount` | `number` | フィルタ前の総件数 |

#### `WorkerFilterState` 型（シフトカレンダー用）

```typescript
interface WorkerFilterState {
  departmentId: string | null;  // null = 「すべて」
  positionId: string | null;    // null = 「すべて」
  nameQuery: string;            // 空文字 = フィルタなし
}
```

### `frontend/components/workers/WorkerListFilter.tsx`（新規）

Worker管理ページ用フィルタUIコンポーネント。

#### Props

| Prop | 型 | 説明 |
|------|----|------|
| `departments` | `Department[]` | 所属課リスト |
| `skillRanks` | `TenantSkillRank[]` | スキルランクリスト |
| `employmentTypes` | `EmploymentType[]` | 雇用形態リスト |
| `filterState` | `WorkerFilterState` | 現在のフィルタ状態 |
| `onChange` | `(next: WorkerFilterState) => void` | フィルタ変更コールバック |
| `onReset` | `() => void` | 全フィルタリセットコールバック |
| `filteredCount` | `number` | フィルタ後の件数 |
| `totalCount` | `number` | フィルタ前の総件数 |

#### `WorkerFilterState` 型（Worker管理ページ用）

```typescript
interface WorkerFilterState {
  departmentId: string | null;     // null = 「すべて」
  skillRankId: string | null;      // null = 「すべて」
  employmentTypeId: string | null; // null = 「すべて」
  nameQuery: string;               // 空文字 = フィルタなし
}
```

### `frontend/components/shift-calendar/WorkerListPanel.tsx`（変更）

- `WorkerFilterBar` をパネルヘッダーに統合
- `useState<WorkerFilterState>` でフィルタ状態を管理
- `filteredWorkers` を `useMemo` で計算（`sortedAvailableWorkers` または `workers` の後段に適用）
- ワーカーリストの描画対象を `filteredWorkers` に変更
- フィルタ条件に一致するワーカーが0件の場合は「条件に一致する対応者がいません」を表示

### `frontend/components/workers/WorkerList.tsx`（変更）

- `WorkerListFilter` をテーブル上部に統合
- `useState<WorkerFilterState>` でフィルタ状態を管理
- `filteredWorkers` を `useMemo` で計算
- ワーカーリストの描画対象を `filteredWorkers` に変更
- フィルタ条件に一致するワーカーが0件の場合は「条件に一致する対応者がいません」を表示
- フィルタ適用中は件数を `filteredCount/totalCount 件` で表示

---

## フィルタ動作仕様

### シフトカレンダー用

| フィルタ種別 | 適用条件 |
|---|---|
| 所属課 | `Worker.department_id === filterState.departmentId`（`null` の場合は全通過） |
| 役職 | `Worker.position_id === filterState.positionId`（`null` の場合は全通過） |
| 氏名 | `matchesNormalized(worker.name, filterState.nameQuery)`（空文字の場合は全通過） |

### Worker管理ページ用

| フィルタ種別 | 適用条件 |
|---|---|
| 所属課 | `Worker.department_id === filterState.departmentId`（`null` の場合は全通過） |
| スキルランク | `Worker.skill_rank_id === filterState.skillRankId`（`null` の場合は全通過） |
| 雇用形態 | `Worker.employment_type_id === filterState.employmentTypeId`（`null` の場合は全通過） |
| 氏名 | `matchesNormalized(worker.name, filterState.nameQuery)`（空文字の場合は全通過） |

- すべてのフィルタは **AND 条件** で複合的に機能する
- 「クリア」ボタンで全フィルタを一括クリアできる（フィルタ適用中のみ表示）

---

## UI/UX

### シフトカレンダー用

- フィルタUIはパネルヘッダー内の既存コントロール（全表示チェックボックス）の上に配置
- フィルタ適用中（いずれか1つ以上が非デフォルト値）は `border-blue-300` でハイライト表示
- 氏名入力欄の右端にクリアボタン（×）を配置。ワンクリックで入力をリセット
- フィルタ適用中はカウント表示（例: `3/10`）を「フィルタをリセット」ボタンと並べて表示

### Worker管理ページ用

- フィルタUIはテーブル上部に配置
- フィルタ適用中は `border-blue-300 bg-blue-50` でハイライト表示
- フィルタ条件が1件以上選択されている場合に「クリア」ボタンと件数（例: `3/10 件`）を表示

