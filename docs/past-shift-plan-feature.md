# 過去シフトプラン参照・モード切り替え機能 仕様書

## 概要

`/shift-requirements` 画面でシフト表を作成・閲覧するための機能です。
シフトプラン（`ShiftPlan` レコード）の有無とユーザー操作に応じて、以下の 3 つのフローが存在します。

| 状況 | フロー |
|------|--------|
| プランなし・初回アクセス | **新規作成フロー** — バナーの「✨ 新規作成」ボタンでプランを生成してから編集 |
| CSVインポート済みのプランあり | **インポート参照フロー** — 「📋 過去シフト」（読み取り専用）で閲覧し、必要に応じて「✏️ シフト枠編集」タブで編集 |
| 新規作成済みまたはインポート後の編集モード | **編集フロー** — プランIDが確定しているため下書き保存・スナップショット履歴が利用可能 |

---

## データモデルの関係

過去シフトデータと現在のシフト要件データは **別テーブル** に存在します。

| 目的 | テーブル群 |
|------|-----------|
| シフトプラン（新規作成・インポート共通） | `shift_plans` → `shift_slots` → `shift_assignments` |
| 現在のシフト要件・アサイン | `shift_requirements` → `shift_requirement_assignments` |

`POST /api/shift-plans/import` および `POST /api/shift-plans/` はどちらも `shift_plans` 系テーブルに書き込みます。
`GET /api/shift-requirements/` は `shift_requirements` テーブルを読み取るため、両者は独立しています。

---

## API エンドポイント

### 空のシフトプランを新規作成

```
POST /api/shift-plans/
Header: X-Tenant-Id: <tenant_id>
Content-Type: application/json
```

**リクエストボディ:**

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `target_year_month` | string | ✅ | 対象年月（`YYYY-MM` 形式）例: `2026-08` |
| `title` | string | — | プランタイトル。省略時は `"YYYY年M月 シフト"` を自動設定 |
| `created_by` | string | — | 作成者のClerk User ID（省略時は `"user"`） |

**レスポンス（201 Created）:**
```json
{
  "id": "uuid",
  "title": "2026年8月 シフト",
  "target_year_month": "2026-08",
  "status": "draft",
  "slots": []
}
```

**エラー:**

| ステータスコード | 説明 |
|----------------|------|
| `409 Conflict` | 同一年月のプランがすでに存在する |

---

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

### シフト表作成フローの全体像

```
/shift-requirements を開く
  │
  ├─ [プランなし] → 「この月のシフトプランはまだ作成されていません」バナーを表示
  │                  → 「✨ 新規作成」ボタンをクリック
  │                      → POST /api/shift-plans/ で空プランを生成
  │                      → createdPlanId をセット、effectiveMode = "edit" に固定
  │                      → カレンダーが編集モードで表示（下書き保存・履歴ボタンが有効化）
  │
  └─ [インポート済みプランあり] → 「📋 過去シフト」タブが自動選択（読み取り専用）
                                  → 「✏️ シフト枠編集」タブに切り替えると編集可能
                                      → currentPlanId = shiftPlan.id が渡される
                                      → 下書き保存・履歴ボタンが有効化
```

### 表示モードの自動切り替え

`/shift-requirements` ページは、カレンダーが表示している年月をもとに `GET /api/shift-plans/` を呼び出し、結果に応じてモードを自動決定します。

| 状態 | デフォルト表示モード |
|------|---------------------|
| 過去プランが存在し、かつ `createdPlanId` が未設定 | 「📋 過去シフト」（読み取り専用） |
| 過去プランが存在しない、または `createdPlanId` が設定済み | 「✏️ シフト枠編集」 |

ユーザーはインポート済みプランがある場合にタブをクリックすることでいつでも手動で切り替えられます。
月ナビゲーション（前月 / 翌月）で年月が変わると、`viewMode` と `createdPlanId` の両方がリセットされ再び自動判定が行われます。

### `effectivePlanId` の解決ロジック（ShiftCalendar 内）

`ShiftCalendar` コンポーネントは `currentPlanId` と `pastPlan.id` から `effectivePlanId` を決定します。

```
effectivePlanId = currentPlanId ?? pastPlan?.id ?? null
```

| フロー | `currentPlanId` | `pastPlan` | `effectivePlanId` |
|--------|----------------|-----------|------------------|
| 新規作成後（編集モード） | `createdPlanId` | `null` | `createdPlanId` ✅ |
| インポート済み・編集モード | `shiftPlan.id` | `null` | `shiftPlan.id` ✅ |
| インポート済み・閲覧モード | `undefined` | `shiftPlan` | `shiftPlan.id` ✅ |
| プランなし・新規作成前 | `undefined` | `null` | `null` — 下書き保存不可 |

`effectivePlanId` が `null` のとき、下書き保存ボタン（DB スナップショット）・履歴ボタンは非表示になります。localStorage の一時保存は `effectivePlanId` に依存しないため、常に機能します。

### 読み取り専用モード（pastPlan モード）

- カレンダー上の各スロットにドラッグ＆ドロップは行えない
- 保存ボタン・下書き保存ボタン・履歴ボタンは非表示
- 各スロットにはアサインされたワーカー名のみ表示される

---

## 実装ファイル一覧

### バックエンド

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/models/schemas.py` | `ShiftPlanCreate`, `ShiftAssignmentDetail`, `ShiftSlotDetail`, `ShiftPlanDetailResponse` スキーマを追加 |
| `backend/app/services/shift_plan_import_service.py` | `create_empty_shift_plan()`, `get_shift_plan_by_year_month()`, `delete_shift_plan()` 関数を追加 |
| `backend/app/routers/shift_plans.py` | `POST /api/shift-plans/`, `GET /api/shift-plans/`, `DELETE /api/shift-plans/{plan_id}` エンドポイントを追加 |

### フロントエンド

| ファイル | 変更内容 |
|---------|---------|
| `frontend/types/shiftPlan.ts` | `ShiftPlanDetail`, `ShiftSlotDetail`, `ShiftAssignmentDetail` 型を追加 |
| `frontend/hooks/useShiftPlan.ts` | 指定年月のプランを SWR で取得。`createShiftPlan()` Mutation を追加 |
| `frontend/hooks/useDeleteShiftPlan.ts` | シフトプラン削除 API を呼び出す Mutation フック |
| `frontend/components/shift-calendar/ShiftCalendar.tsx` | `pastPlan`, `currentPlanId`, `readOnly`, `onYearMonthChange` プロップを追加。`effectivePlanId` でスナップショット機能を制御 |
| `frontend/app/shift-requirements/page.tsx` | `createdPlanId` 状態・新規作成バナー・モード切り替えタブ・削除確認ダイアログを追加。`createShiftPlan` を `useShiftPlan` から取得 |

---

## 制約・注意事項

- `shift_requirements` テーブルにデータがない状態で `GET /api/shift-requirements/` を呼び出しても空配列が返るのは仕様通りです。プラン系データは `shift_plans` 系テーブルに格納されています。
- `GET /api/shift-plans/` は `shift_requirements` とは独立しているため、両者のデータが同時に存在する場合でも、それぞれ別のエンドポイントから取得されます。
- インポート済みデータの編集・上書きはこの機能のスコープ外です。過去データを修正する場合は再インポートが必要です。
- 新規作成（`POST /api/shift-plans/`）で生成されるプランのステータスは `draft` です。インポート時は `published`（デフォルト）が設定されます。
