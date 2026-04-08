# Bug: 同一年月への再インポートで ShiftPlan レコードが重複蓄積する

**種別**: Bug  
**優先度**: High  
**影響範囲**: `backend/app/services/shift_plan_import_service.py`

---

## 問題の概要

`import_shift_plan()` は、同一テナント・同一年月のデータが既に存在するかを確認せずに毎回 `ShiftPlan` レコードを新規生成します。
そのため、同じ月のCSVを複数回インポートすると `shift_plans` テーブルにレコードが際限なく積み上がります。

```python
# 現在の実装（問題あり）
plan = ShiftPlan(
    id=uuid.uuid4(),
    ...
    target_year_month=target_year_month,  # 重複チェックなし
)
session.add(plan)
```

## 何が問題か

`get_shift_plan_by_year_month()` は `ORDER BY created_at DESC LIMIT 1` で最新1件を取得するため、**画面上は最新データが表示される**。しかし、古いレコード（`shift_slots` / `shift_assignments` を含む）はDBに残り続けます。

- 大量インポートが発生した場合、DBが不要データで肥大化する
- 過去プランの DELETE / RLS 設計に影響が出る
- テナント間でのデータ分離ポリシーを確認・監査する際にノイズになる

## 修正方法

インポート時に同一テナント・同一年月の既存プランを削除（または上書き）してから新規作成する。

```python
# 既存プランを削除してから作成（推奨）
existing_plan = session.exec(
    select(ShiftPlan).where(
        ShiftPlan.tenant_id == tenant_id,
        ShiftPlan.target_year_month == target_year_month,
    )
).first()

if existing_plan is not None:
    session.delete(existing_plan)
    session.flush()
```

`shift_slots` / `shift_assignments` は `ondelete="CASCADE"` 設定済みのため、`ShiftPlan` を削除するだけで関連レコードも自動削除されます。

## 補足

- `shift_slots.plan_id` → `ForeignKey("shift_plans.id", ondelete="CASCADE")` ✅
- `shift_assignments.slot_id` → `ForeignKey("shift_slots.id", ondelete="CASCADE")` ✅
