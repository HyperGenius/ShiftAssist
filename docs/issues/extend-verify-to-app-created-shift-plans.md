---
title: '[Feature]: アプリ内で作成したシフトプランでも Verify を表示できるようにする'
labels: enhancement, development
---

## 概要

現在 Verify 機能（Before/After 集計差分）は、過去シフトをインポートした場合の「📋 過去シフト」ビューでのみ表示される。
アプリ内でシフトを直接作成・編集している「✏️ シフト枠編集」モードでも Verify ボタンを表示し、差分確認ができるよう拡張する。

---

## 目的

* インポートデータがなくてもアプリ内で作成したシフトプランに対して集計 Before/After を確認できる
* Verify の利用範囲を広げ、より多くのユースケースで偏り確認のワークフローを活用できる

---

## 要件

### 1. Verify ボタン表示条件の拡張

* 仕様詳細:
  * 現在: `pastPlan` が存在する場合のみ Verify ボタンを表示
  * 変更後: **保存済みのシフトプラン**（インポート・アプリ作成を問わず）が存在する場合に Verify ボタンを表示
  * 「✏️ シフト枠編集」モード中でも、当月に対応する `ShiftPlanDetail`（`shiftPlan`）が存在すれば Verify ボタンを表示する
* 特殊なルールや例外処理:
  * 未保存（DB 未登録）の状態では Verify は表示しない
  * Verify API に渡す `shiftPlanId` は `pastPlan.id` ではなく、表示中の `ShiftPlanDetail.id` を使用する

### 2. `ShiftCalendar` コンポーネントへの props 変更

* 仕様詳細:
  * `ShiftCalendarProps` に `currentPlanId?: string | null` を追加し、edit モード時の保存済みプラン ID を渡せるようにする
  * Verify ボタンの表示条件: `pastPlan?.id ?? currentPlanId` が存在する場合に表示
  * `ShiftVerifyDialog` に渡す `shiftPlanId`: `pastPlan?.id ?? currentPlanId`
* UI/UX 上の演出:
  * edit モードでの Verify ボタンのラベル・見た目は過去シフトモードと同一で問題ない（🔍 Verify）

---

## 技術的な実装方針

### Backend (`backend/`)

1. **データ定義・モデル:**
   - 変更なし。既存の `GET /api/tenants/{tenant_id}/shift-plans/{shift_plan_id}/verify` エンドポイントはアプリ作成のシフトプランにも同様に適用できる

2. **ロジック・サービス:**
   - 変更なし。`get_shift_verify_stats()` は `shift_plan_id` から `ShiftPlan` を引けるすべてのケースに対応済み

3. **APIエンドポイント:**
   - 変更なし

### Frontend (`frontend/`)

1. **コンポーネント・UI:**
   - `frontend/components/shift-calendar/ShiftCalendar.tsx`
     - `ShiftCalendarProps` に `currentPlanId?: string | null` を追加
     - Verify ボタンの条件を `pastPlan` のみから `pastPlan?.id ?? currentPlanId` に変更
     - `ShiftVerifyDialog` の `shiftPlanId` prop も同様に変更
   - `frontend/app/shift-requirements/page.tsx`
     - `ShiftCalendar` に `currentPlanId={effectiveMode === "edit" ? shiftPlan?.id : undefined}` を追加で渡す

2. **状態管理・Hooks:**
   - 変更なし。`useShiftPlan` が返す `shiftPlan.id` をそのまま利用する

---

## 完了条件 (Acceptance Criteria)

* [ ] 「✏️ シフト枠編集」モードで保存済みシフトプランが存在するとき、🔍 Verify ボタンが表示される
* [ ] Verify ボタン押下時に `ShiftVerifyDialog` が開き、アプリ作成シフトの Before/After 集計が表示される
* [ ] 「📋 過去シフト」モードでの Verify 動作は変わらない（リグレッションなし）
* [ ] 未保存・未作成状態（`shiftPlan` が null）では Verify ボタンが表示されない
* [ ] 関連ドキュメント(`docs`ディレクトリ)が最新化されている

---

## 作業のヒント・メモ

> [!TIP]
> - Verify ボタンの表示ロジックは `ShiftCalendar.tsx` の以下の箇所にある
>   ```tsx
>   // 変更前
>   {pastPlan && (
>     <Button ... onClick={() => setShowVerifyDialog(true)}>
>       🔍 Verify
>     </Button>
>   )}
>   // Verify ダイアログ
>   {pastPlan && (
>     <ShiftVerifyDialog
>       shiftPlanId={pastPlan.id}
>       yearMonth={pastPlan.target_year_month}
>       ...
>     />
>   )}
>   ```
> - `page.tsx` では `shiftPlan` が `useShiftPlan()` から取得され、edit モードでも参照可能
> - `yearMonth` は `pastPlan.target_year_month` の代わりに `${year}-${String(month).padStart(2, "0")}` を使用できる

## 関連Issue

- #144（feat: シフトカレンダー Verify 機能（Before/After 集計差分））
