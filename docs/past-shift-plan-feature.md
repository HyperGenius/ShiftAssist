# 過去シフトプラン参照・モード切り替え機能 仕様書

## 概要

CSVインポートで投入した過去シフトデータを、シフト枠カレンダー画面（`/shift-requirements`）でそのまま閲覧できる機能です。
対象年月に過去インポートデータが存在する場合は「📋 過去シフト（閲覧専用）」タブを自動表示し、存在しない場合は従来の「✏️ シフト枠編集」モードで直接開きます。

---

## データモデルの関係

過去シフトデータと現在のシフト要件データは **別テーブル** に存在します。

| 目的 | テーブル群 |
|------|-----------|
| 過去シフトインポートデータ | `shift_plans` → `shift_slots` → `shift_assignments` |
| 現在のシフト要件・アサイン | `shift_requirements` → `shift_requirement_assignments` |

`POST /api/shift-plans/import` はインポートデータを `shift_plans` 系テーブルに書き込みます。
`GET /api/shift-requirements/` は `shift_requirements` テーブルを読み取るため、両者は独立しています。

---

## API エンドポイント

### 過去シフトプラン取得

```
GET /api/shift-plans/?year_month=YYYY-MM
Header: X-Tenant-Id: <tenant_id>
```

**クエリパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `year_month` | string | ✅ | 対象年月（`YYYY-MM` 形式）例: `2025-06` |

**レスポンス（プランあり）:**
```json
{
  "id": "uuid",
  "title": "2025-06 インポート",
  "target_year_month": "2025-06",
  "status": "published",
  "slots": [
    {
      "id": "uuid",
      "date": "2025-06-01T00:00:00",
      "slot_type": "weekday_night",
      "assignments": [
        {
          "id": "uuid",
          "worker_id": "uuid",
          "is_manual_override": true
        }
      ]
    }
  ]
}
```

**レスポンス（プランなし）:**
```json
null
```

同一年月に複数のプランが存在する場合は、作成日時が最新のものを返します。

---

### 過去シフトプラン削除

```
DELETE /api/shift-plans/{plan_id}
Header: X-Tenant-Id: <tenant_id>
```

**パスパラメータ:**

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `plan_id` | UUID | ✅ | 削除対象のシフトプランID |

**レスポンス:**

| ステータスコード | 説明 |
|----------------|------|
| `204 No Content` | 削除成功 |
| `404 Not Found` | 指定された `plan_id` が存在しない、またはリクエストユーザーのテナントに属さない場合 |

削除時、紐づく `ShiftSlot` および `ShiftAssignment` は外部キーの `ondelete="CASCADE"` 設定により自動削除されます。

---

## フロントエンド動作仕様

### 表示モードの自動切り替え

`/shift-requirements` ページは、カレンダーが表示している年月をもとに `GET /api/shift-plans/` を呼び出し、結果に応じてモードを自動決定します。

| 状態 | デフォルト表示モード |
|------|---------------------|
| 過去プランが存在する | 「📋 過去シフト」（読み取り専用） |
| 過去プランが存在しない | 「✏️ シフト枠編集」 |

ユーザーはタブをクリックすることでいつでも手動で切り替えられます。
月ナビゲーション（前月 / 翌月）で年月が変わると、モード選択はリセットされ再び自動判定が行われます。

### 読み取り専用モード（pastPlan モード）

- カレンダー上の各スロットにドラッグ＆ドロップは行えない
- 保存ボタンは非表示
- 各スロットにはアサインされたワーカー名のみ表示される

---

## 実装ファイル一覧

### バックエンド

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/models/schemas.py` | `ShiftAssignmentDetail`, `ShiftSlotDetail`, `ShiftPlanDetailResponse` スキーマを追加 |
| `backend/app/services/shift_plan_import_service.py` | `get_shift_plan_by_year_month()`, `delete_shift_plan()` 関数を追加 |
| `backend/app/routers/shift_plans.py` | `GET /api/shift-plans/`, `DELETE /api/shift-plans/{plan_id}` エンドポイントを追加 |

### フロントエンド

| ファイル | 変更内容 |
|---------|---------|
| `frontend/types/shiftPlan.ts` | `ShiftPlanDetail`, `ShiftSlotDetail`, `ShiftAssignmentDetail` 型を追加 |
| `frontend/hooks/useShiftPlan.ts` | 新規作成。指定年月の過去プランを SWR で取得 |
| `frontend/hooks/useDeleteShiftPlan.ts` | 新規作成。シフトプラン削除 API を呼び出す Mutation フック |
| `frontend/components/shift-calendar/ShiftSlot.tsx` | `readOnly` プロップを追加。true 時はドロップゾーンの代わりにワーカー名を表示 |
| `frontend/components/shift-calendar/CalendarCell.tsx` | `readOnly` プロップを追加し `ShiftSlot` へ伝播 |
| `frontend/components/shift-calendar/ShiftCalendar.tsx` | `pastPlan`, `readOnly`, `onYearMonthChange` プロップを追加 |
| `frontend/app/shift-requirements/page.tsx` | `useShiftPlan`, `useDeleteShiftPlan` フックを統合し、モード切り替えタブ・削除ボタン・確認ダイアログ UI を追加 |

---

## 制約・注意事項

- `shift_requirements` テーブルにデータがない状態で `GET /api/shift-requirements/` を呼び出しても空配列が返るのは仕様通りです。過去インポートデータは `shift_plans` 系テーブルに格納されています。
- `GET /api/shift-plans/` は `shift_requirements` とは独立しているため、両者のデータが同時に存在する場合でも、それぞれ別のエンドポイントから取得されます。
- インポート済みデータの編集・上書きはこの機能のスコープ外です。過去データを修正する場合は再インポートが必要です。
