# シフト集計機能 (aggregate-stats)

## 概要

Worker単位のシフト集計ページ。ユーザーが任意の年月を選択し、
そこから過去12ヶ月間の `SlotTypeEnum` 単位の合計・平均シフト回数を一覧表示する。

集計データは専用テーブル `worker_monthly_slot_stats` に保存し、
DBへの繰り返し集計クエリ負荷を回避する設計となっている。

---

## 1. データモデル

### `worker_monthly_slot_stats` テーブル

| カラム名    | 型           | 説明                                                        |
|------------|-------------|-------------------------------------------------------------|
| id         | UUID PK     | プライマリキー                                               |
| tenant_id  | String      | テナントID                                                   |
| worker_id  | UUID FK     | ワーカーID (`workers.id`)                                   |
| year_month | String      | 集計対象年月（`YYYY-MM` 形式）                               |
| slot_type  | SlotTypeEnum | 枠種別                                                     |
| weekday    | Integer?    | 曜日（0=月〜3=木）。`weekday_night` 以外は `NULL`           |
| count      | Integer     | シフト回数                                                   |
| updated_at | DateTime    | 最終更新日時                                                 |

ユニーク制約: `(tenant_id, worker_id, year_month, slot_type, weekday)`

---

## 2. 集計ロジック

### 集計期間

- 選択月を **末月** として直近12ヶ月を集計対象とする
- 例: 2026年4月選択 → 2025年5月〜2026年4月

### 対象データ

- `published` ステータスの `ShiftPlan` に紐づく `ShiftAssignment` のみ集計対象

### `weekday_night` の曜日分割

- `weekday_night` 枠のみ、`ShiftSlot.date` から PostgreSQL `EXTRACT(isodow, ...)` を使って曜日を取得する
- `isodow` の値: 1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日
- 月〜木（1〜4）のみ weekday=0〜3 として集計する
- 金〜日は `weekday=NULL` としてまとめる

### 有効月数の正規化 (`_compute_effective_months_for_aggregate`)

| 条件                                           | 有効月数                  |
|-----------------------------------------------|--------------------------|
| `joined_at` が `NULL` または集計開始月より前   | 12ヶ月                    |
| `joined_at` が集計期間内（途中採用・転入）       | `joined_at`月〜選択月の月数 |
| `joined_at` が集計終了月より後                 | 1.0（最低値）             |

---

## 3. Upsert タイミング

`ShiftPlan` のステータスが `published` に変更されるタイミングで
`upsert_monthly_slot_stats(session, tenant_id, year_month)` が呼び出される。

現在は以下のエンドポイントから呼び出し:

- `POST /api/shift-plans/import` (`shift_plan_import_service.import_shift_plan`)

> **⚠️ 注意**: 通常の運用フロー（`ShiftRequirementAssignment` ベースの確定）では、
> `upsert_monthly_slot_stats` は**自動的に呼ばれない**。
> このため、通常フローで確定したシフトプランは `worker_monthly_slot_stats` テーブルに
> 自動反映されない。
>
> 最新の集計データを得るには、集計ページの**「再計算」ボタン**を手動で実行すること。
>
> 詳細実装（通常確定フローへの `upsert_monthly_slot_stats` 自動呼び出し追加）は
> 別 Issue として管理する。

---

## 4. APIエンドポイント

```
GET /api/tenants/{tenant_id}/worker-stats/aggregate?year_month=YYYY-MM
```

- クエリパラメーター `year_month`: 省略時は当月
- レスポンス: `AggregateStatsResponse`

### レスポンス例

```json
{
  "year_month": "2026-04",
  "period_months": 12,
  "items": [
    {
      "worker_id": "...",
      "worker_name": "山田 太郎",
      "effective_months": 12.0,
      "position_name": "主任",
      "department_name": "1課",
      "skill_rank_name": "A",
      "employment_type_name": null,
      "is_non_default_employment": false,
      "joined_at": "2024-04-01",
      "skill_acquired_at": null,
      "slot_stats": [
        {
          "slot_type": "weekday_night",
          "count": 36,
          "monthly_avg": 3.0,
          "weekday_stats": [
            { "weekday": 0, "count": 9, "monthly_avg": 0.75 },
            { "weekday": 1, "count": 10, "monthly_avg": 0.83 },
            { "weekday": 2, "count": 8, "monthly_avg": 0.67 },
            { "weekday": 3, "count": 9, "monthly_avg": 0.75 }
          ]
        },
        { "slot_type": "sat_day", "count": 6, "monthly_avg": 0.5, "weekday_stats": null }
      ]
    }
  ]
}
```

### N+1 問題回避

`get_aggregate_stats` では、Workers クエリに加えて以下の関連テーブルをバッチクエリ（各1回）で取得し、
Python 辞書でルックアップを行うことで N+1 問題を回避している:

- `positions` テーブル → `position_map: dict[UUID, str]`
- `departments` テーブル → `department_map: dict[UUID, str]`
- `tenant_skill_ranks` テーブル → `skill_rank_map: dict[UUID, str]`
- `employment_types` テーブル → `employment_type_map: dict[UUID, tuple[str, bool]]`

---

## 5. フロントエンド

### ページ

- パス: `/admin/aggregate-stats`
- コンポーネント: `AggregateStatsContent` (client component)

### コンポーネント構成

```
app/admin/aggregate-stats/page.tsx      # ページ（Server Component）
components/aggregate-stats/
  AggregateStatsContent.tsx             # 年月セレクター + テーブルの統合コンテナ
  YearMonthPicker.tsx                   # 年・月セレクトボックス
  AggregateStatsTable.tsx               # Worker行 × SlotType列のテーブル（ソート・sticky対応）
components/ui/
  WorkerAttributeBadge.tsx              # 有効月数バッジ（InfoBadge）・雇用形態バッジ（EmploymentTypeBadge）
hooks/useAggregateStats.ts              # SWRフック
types/workerStats.ts                    # 型定義（AggregateStatsResponse等）
```

### テーブルレイアウト（2段ヘッダー）

```
| 対応者名 | 役職 | 所属課 | スキル | 有効月数 | ←── 平日夜（曜日別）───→ | 祝前夜 | ←土曜日→ | ←日祝→ | ←連休→ |
|---------|------|-------|-------|---------|月|火|水|木|---------|昼|夜|昼|夜|昼|夜|
```

- カラム順: 対応者名 → 役職 → 所属課 → スキルランク → 有効月数 → 平日夜（月〜木） → 祝前夜 → 土昼/土夜 → 日祝昼/日祝夜 → 連休昼/連休夜
- `weekday_night` 列はヘッダーを結合して4曜日のサブカラムに展開する
- 各セルに合計回数（上段）と月平均（下段、小数1桁）を表示する

### Sticky（固定）設定

| 要素                        | CSS クラス                          | z-index |
|----------------------------|--------------------------------------|---------|
| テーブルコンテナ             | `max-h-[70vh] overflow-auto`         | —       |
| thead                       | `sticky top-0 z-20`                 | 20      |
| 左固定列（対応者名〜スキル） | `sticky left-0/120px/200px/300px z-30`（ヘッダー）<br>`sticky left-0/... z-10`（データ行） | 30 (header) / 10 (row) |

### バッジ表示

| バッジ            | 表示条件                                        | ツールチップ             |
|------------------|-------------------------------------------------|--------------------------|
| `InfoBadge` (ⓘ) | `joined_at` or `skill_acquired_at` から算出した月数が12未満 | 「有効月数: N ヶ月」      |
| `EmploymentTypeBadge` | `is_non_default_employment = true`（非デフォルト雇用形態 or is_special） | 雇用形態名 |

### ソート機能

- ソート対象カラム: 対応者名・役職・所属課・スキルランク・有効月数・各 SlotType（合計回数）
- **デフォルト**: 所属課名の昇順
- フロントエンド側でのみソート処理（API 再取得なし）
- ヘッダークリックで昇順 ↔ 降順切り替え
- 現在のソート状態は ▲/▼ アイコンで表示
