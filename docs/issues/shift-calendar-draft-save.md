---
title: '[Feature]: シフトカレンダー途中保存機能'
labels: enhancement, development
---

## 概要

シフトカレンダーの編集内容を途中保存できる機能を追加する。
**一時保存**（localStorage）と**下書き保存**（クラウドDB）の2段階の保存方式を実装する。

## 目的

- カレンダー作成者が作業途中にデスクを離れても、編集内容が失われないようにする
- 将来的に、モバイル端末・異なる端末・複数担当者による共同作成に対応する基盤を作る

## 要件

### 1. 一時保存機能（localStorage）

* **仕様詳細:**
  - ユーザーの操作（アサイン追加・削除・人数変更）ごとに `calendarState` を localStorage へ保存する
  - 保存はDebounce（例: 1000ms）して頻繁な書き込みを抑制する
  - localStorage キーは `shift-draft:{tenantId}:{departmentId}:{YYYY-MM}` 形式とし、テナント・部署・年月で一意にする
  - 保存データには `calendarState` 本体に加え、保存日時（ISO 8601）を含める
  - localStorage の容量制限（5MB程度）を考慮し、データが大きすぎる場合は保存を省略してコンソールへ警告を出す

* **特殊なルールや例外処理:**
  - ページ遷移時（`beforeunload` または Next.js の `router.events`）に、localStorage のタイムスタンプとDBの `updated_at` を比較する
  - localStorage のタイムスタンプが新しい場合は「未保存のデータがあります。復元しますか？」バナーを表示する
  - 復元・破棄のどちらかを選択させ、破棄時は localStorage エントリを削除する
  - `readOnly` モードの場合は一時保存を行わない

### 2. 下書き保存機能（クラウドDB スナップショット）

* **仕様詳細:**
  - 「下書き保存」ボタンクリック時に、その時点のシフトカレンダーデータ（`calendarState`相当のJSON）をDBへ保存する
  - スナップショット方式で過去5回分の履歴を保持する（6件目の保存時に最も古いものを削除）
  - `ShiftPlanSnapshot` テーブルを新設し、シフトプランID・スナップショットデータ（JSONB）・保存者Clerk User ID・保存日時を記録する
  - 保存成功時に localStorage の該当エントリを削除する

* **UI/UX上の演出:**
  - 復元ダイアログでは各スナップショットの「保存日時」「保存者表示名」を一覧表示し、どのスナップショットを復元するか選択できる
  - 復元後はカレンダー状態が上書きされる旨を確認ダイアログで警告する
  - 保存中はボタンをローディング状態にし、完了後 toast で「下書きを保存しました」と通知する

## 技術的な実装方針

### Backend (`backend/`)

1. **データ定義・モデル (`app/models/models.py`):**
   - `ShiftPlanSnapshot` モデルを新設する
     ```
     id: UUID (PK)
     tenant_id: String (index)
     shift_plan_id: UUID (FK → shift_plans.id, CASCADE)
     snapshot_data: JSON  # CalendarState相当のJSON
     created_by: String   # Clerk User ID
     created_at: DateTime
     ```
   - `ShiftPlan` モデルに `updated_at: DateTime` カラムを追加する（LocalStorageタイムスタンプ比較用）

2. **ロジック・サービス (`app/services/shift_plan_snapshot_service.py`):**
   - `create_snapshot(session, tenant_id, plan_id, data, created_by)`: スナップショット作成。保存後、同プランの件数が5を超えたら最古のものを削除する
   - `list_snapshots(session, tenant_id, plan_id)`: スナップショット一覧取得（降順、最大5件）
   - `restore_snapshot(session, tenant_id, plan_id, snapshot_id)`: 指定スナップショットのデータを返す

3. **APIエンドポイント (`app/routers/shift_plans.py`):**
   - `POST /api/shift-plans/{plan_id}/snapshots` — 下書きスナップショット作成
   - `GET  /api/shift-plans/{plan_id}/snapshots` — スナップショット一覧取得（`created_by`, `created_at` を含む）
   - `GET  /api/shift-plans/{plan_id}/updated-at` — `ShiftPlan.updated_at` を返す（ローカルタイムスタンプとの比較用）

### Frontend (`frontend/`)

1. **コンポーネント・UI:**
   - `components/shift-calendar/DraftSaveButton.tsx` — 「下書き保存」ボタン（ローディング状態付き）
   - `components/shift-calendar/SnapshotHistoryDialog.tsx` — 復元ダイアログ（保存日時・保存者名の一覧・選択・復元）
   - `components/shift-calendar/UnsavedDataBanner.tsx` — ページ遷移時の未保存警告バナー（復元 / 破棄ボタン付き）

2. **状態管理・Hooks:**
   - `hooks/useLocalStorageDraft.ts` — `calendarState` のDebounce localStorage保存・読み込み・タイムスタンプ取得、localStorage 容量チェックを担当する
   - `hooks/useShiftSnapshot.ts` — スナップショット一覧取得 (SWR)、作成・復元ミューテーションを担当する
   - `ShiftCalendar.tsx` に `useLocalStorageDraft` と `useShiftSnapshot` を組み込み、下書き保存ボタン・復元ダイアログ・未保存警告の制御を追加する

## 完了条件 (Acceptance Criteria)

* [ ] シフトカレンダーを操作すると1秒後に localStorage へ自動保存される
* [ ] ページをリロード・離脱する際、localStorage に未保存データがある場合は警告バナーが表示される
* [ ] 「復元する」を選ぶと localStorage の状態がカレンダーに反映される
* [ ] 「破棄する」を選ぶと localStorage エントリが削除される
* [ ] 「下書き保存」ボタンをクリックするとDBにスナップショットが作成される
* [ ] スナップショットは最大5件保持され、6件目の保存時に最古のものが自動削除される
* [ ] 復元ダイアログに保存日時と保存者名が表示される
* [ ] 選択したスナップショットを復元するとカレンダー状態が上書きされる
* [ ] `readOnly` モード時は一時保存・下書き保存ともに無効化される
* [ ] localStorage が容量超過する場合は保存を省略しコンソール警告を出す
* [ ] Alembicマイグレーションが作成され、`ShiftPlanSnapshot` テーブルと `ShiftPlan.updated_at` カラムが追加されている
* [ ] 途中保存機能の仕様が`docs`ディレクトリに作成されている

## 作業のヒント・メモ

> [!TIP]
> - `calendarState` の型は `frontend/types/shiftRequirement.ts` の `CalendarState`
> - localStorage への Debounce 保存は `useEffect` + `useRef` でタイマーIDを管理する実装が適切
> - スナップショットデータの Clerk User ID → 表示名の解決は Clerk の `useOrganization` や `clerkClient` を利用する
> - `ShiftPlan.updated_at` の追加に伴い `ShiftPlanDetailResponse` スキーマも更新が必要
> - 既存の `shift_plans.py` ルーターにエンドポイントを追加する。スナップショット件数が増えた場合の削除は `create_snapshot` サービス内でトランザクションを共有して行う
> - localStorage キーの衝突を防ぐため、テナントID・部署ID・年月をすべて含めること

## 関連Issue

- #
