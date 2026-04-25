# シフトカレンダー途中保存機能

## 概要

シフトカレンダーの編集内容を途中保存できる機能。
**一時保存**（localStorage）と**下書き保存**（クラウドDB スナップショット）の2段階の保存方式を実装する。

## 目的

- カレンダー作成者が作業途中にデスクを離れても、編集内容が失われないようにする
- 将来的に、モバイル端末・異なる端末・複数担当者による共同作成に対応する基盤を作る

---

## 1. 一時保存機能（localStorage）

### 仕様

| 項目 | 詳細 |
|------|------|
| トリガー | ユーザー操作（アサイン追加・削除・人数変更）ごとに debounce（1000ms）して保存 |
| キー形式 | `shift-draft:{tenantId}:{departmentId}:{YYYY-MM}` |
| 保存データ | `calendarState` 本体 + `savedAt`（ISO 8601） |
| 容量制限 | 5MB 超の場合は保存を省略してコンソール警告 |
| readOnly | `readOnly=true` 時は一時保存を行わない |

### 復元フロー

1. ページマウント時に localStorage の下書きタイムスタンプを確認
2. 下書きが存在する場合、黄色のバナー（`UnsavedDataBanner`）を表示
3. **「復元する」** → localStorage の `calendarState` をカレンダーに反映し、エントリを削除
4. **「破棄する」** → localStorage エントリを削除

### 実装ファイル

- `frontend/hooks/useLocalStorageDraft.ts` — debounce 保存・読み込み・削除・タイムスタンプ取得
- `frontend/components/shift-calendar/UnsavedDataBanner.tsx` — バナー UI

---

## 2. 下書き保存機能（クラウドDB スナップショット）

### 仕様

| 項目 | 詳細 |
|------|------|
| トリガー | 「下書き保存」ボタンクリック |
| 保存先 | `shift_plan_snapshots` テーブル |
| 保持件数 | 最大 5 件（6件目で最古を自動削除） |
| 保存内容 | `snapshot_data`（CalendarState JSON）、`created_by`（Clerk User ID）、`created_at` |
| 成功後 | localStorage の対応エントリを削除 + toast 通知 |

### APIエンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| `POST` | `/api/shift-plans/{plan_id}/snapshots` | スナップショット作成 |
| `GET` | `/api/shift-plans/{plan_id}/snapshots` | スナップショット一覧（降順・最大5件） |
| `GET` | `/api/shift-plans/{plan_id}/updated-at` | `ShiftPlan.updated_at` 取得 |

### 復元フロー

1. 「📋 履歴」ボタンをクリック → `SnapshotHistoryDialog` を表示
2. 各スナップショットの保存日時・保存者 ID を一覧表示
3. 選択して「復元する」をクリック → 確認ダイアログ表示
4. 確認後、選択スナップショットの `snapshot_data` でカレンダー状態を上書き

### 実装ファイル

- `frontend/hooks/useShiftSnapshot.ts` — SWR によるスナップショット一覧取得・作成
- `frontend/components/shift-calendar/DraftSaveButton.tsx` — 下書き保存ボタン
- `frontend/components/shift-calendar/SnapshotHistoryDialog.tsx` — 履歴・復元ダイアログ

---

## 3. DBスキーマ変更

### 新設テーブル: `shift_plan_snapshots`

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | UUID (PK) | プライマリキー |
| `tenant_id` | String (index) | テナントID |
| `shift_plan_id` | UUID (FK → shift_plans.id, CASCADE) | シフトプランID |
| `snapshot_data` | JSON | CalendarState 相当のJSONデータ |
| `created_by` | String | 保存者 Clerk User ID |
| `created_at` | DateTime | 保存日時 |

### 変更テーブル: `shift_plans`

| カラム | 型 | 説明 |
|--------|-----|------|
| `updated_at` | DateTime (nullable) | 最終更新日時（追加） |

### マイグレーション

`backend/alembic/versions/s9t0u1v2w3x4_.py`

---

## 4. readOnly モードの挙動

- `readOnly=true` の場合、localStorage への自動保存・バナー表示・下書き保存ボタン・履歴ボタンはすべて非表示/無効化される

---

## 5. 完了条件

- [x] シフトカレンダーを操作すると1秒後に localStorage へ自動保存される
- [x] ページをリロード・マウント時、localStorage に未保存データがある場合はバナーが表示される
- [x] 「復元する」を選ぶと localStorage の状態がカレンダーに反映される
- [x] 「破棄する」を選ぶと localStorage エントリが削除される
- [x] 「下書き保存」ボタンをクリックするとDBにスナップショットが作成される
- [x] スナップショットは最大5件保持され、6件目の保存時に最古のものが自動削除される
- [x] 復元ダイアログに保存日時と保存者IDが表示される
- [x] 選択したスナップショットを復元するとカレンダー状態が上書きされる
- [x] `readOnly` モード時は一時保存・下書き保存ともに無効化される
- [x] localStorage が容量超過する場合は保存を省略しコンソール警告を出す
- [x] Alembicマイグレーションが作成され、`ShiftPlanSnapshot` テーブルと `ShiftPlan.updated_at` カラムが追加されている
