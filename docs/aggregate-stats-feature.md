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
  AggregateStatsTable.tsx               # Worker行 × SlotType列のテーブル
hooks/useAggregateStats.ts              # SWRフック
types/workerStats.ts                    # 型定義（AggregateStatsResponse等）
```

### テーブルレイアウト

| 対応者 | 有効月数 | ←── 平日夜（曜日別）───→ | 土昼 | 土夜 | ... |
|--------|---------|月|火|水|木|------|------|-----|
| 山田太郎 | 12.0 | 9 | 10 | 8 | 9 | 6 | 3 | ... |

- `weekday_night` 列はヘッダーを結合して4曜日のサブカラムに展開する
- 各セルに合計回数（上段）と月平均（下段、小数1桁）を表示する
