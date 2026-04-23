# シフト Verify 機能

## 概要

シフトカレンダー作成時に、新規シフトを適用した場合の集計 Before/After を表示し、
Worker 間のスロットアサイン偏りを事前に確認できる「Verify 機能」。

DB への登録を行わず一時的な集計を返すことで、確定前の差分確認（Before/After）を提供する。

---

## 1. Before/After の定義

- **Before**: シフトカレンダー作成月の **1 ヶ月前** を末月とした直近 12 ヶ月
  - 例: 2026 年 6 月作成 → 2025-06 〜 2026-05
- **After**: シフトカレンダー作成月を末月とした直近 12 ヶ月
  - 例: 2026 年 6 月作成 → 2025-07 〜 2026-06
- 集計対象: 各 Worker の各スロット (`SlotTypeEnum`) へのアサイン回数
- Before は既存の `worker_monthly_slot_stats` テーブルから取得
- After は Before の集計データ + 今回の `ShiftPlan` のアサインを加算して一時算出（DB 保存なし）

---

## 2. API エンドポイント

### `GET /api/tenants/{tenant_id}/shift-plans/{shift_plan_id}/verify`

- **認証**: `X-Tenant-Id` ヘッダーによるテナントアイソレーション
- **DB 書き込み**: なし（参照のみ）
- **レスポンス**: `ShiftVerifyResponse`

#### レスポンス例

```json
{
  "year_month": "2026-06",
  "before_period": "2025-06 〜 2026-05",
  "after_period": "2025-07 〜 2026-06",
  "items": [
    {
      "worker_id": "...",
      "worker_name": "田中 太郎",
      "department_name": "外来",
      "effective_months": 12.0,
      "slot_stats": [
        {
          "slot_type": "sat_day",
          "before_count": 10,
          "before_monthly_avg": 0.83,
          "after_count": 12,
          "after_monthly_avg": 1.0,
          "delta_count": 2,
          "is_outlier": false,
          "weekday_stats": null
        }
      ]
    }
  ]
}
```

#### エラー

| ステータス | 説明 |
|-----------|------|
| 404       | `shift_plan_id` に対応する `ShiftPlan` が存在しない |

---

## 3. outlier 判定ロジック

- 各 `SlotType` ごとに、全 Worker の After 月平均を集計する
- 平均値 (mean) と標準偏差 (σ) を算出する
- **閾値** = mean + σ
- あるWorkerの After 月平均 > 閾値 の場合、`is_outlier = true` をセット
- 全 Worker が同じ月平均の場合（σ = 0）は誰も outlier にならない

---

## 4. 有効月数の正規化

- Before: `_compute_effective_months_for_aggregate(worker.joined_at, before_start_ym, before_end_ym)`
- After: `_compute_effective_months_for_aggregate(worker.joined_at, after_start_ym, after_end_ym)`
- Before 集計が存在しない新規 Worker でも `before_count = 0` として表示し、エラーにならない

---

## 5. 実装ファイル

### Backend

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/services/shift_verify_service.py` | 新規作成。`get_shift_verify_stats()` 実装 |
| `backend/app/models/schemas.py` | `ShiftVerifyResponse` 等のスキーマ追加 |
| `backend/app/routers/worker_stats.py` | `GET .../verify` エンドポイント追加 |
| `backend/tests/unit/test_shift_verify_service.py` | 新規テスト追加 |

### Frontend

| ファイル | 変更内容 |
|---------|---------|
| `frontend/types/workerStats.ts` | `ShiftVerifyResponse` 等の型追加 |
| `frontend/hooks/useShiftVerify.ts` | 新規フック作成 |
| `frontend/components/shift-calendar/ShiftVerifyTable.tsx` | Before/After テーブル新規作成 |
| `frontend/components/shift-calendar/ShiftVerifyDialog.tsx` | モーダルダイアログ新規作成 |
| `frontend/components/shift-calendar/ShiftCalendar.tsx` | Verify ボタン + ダイアログ追加 |

---

## 6. UI 操作フロー

1. シフト枠カレンダー画面で過去シフトプランを選択すると「🔍 Verify」ボタンが表示される
2. ボタン押下で `ShiftVerifyDialog` が開く
3. ダイアログ内で Before/After の月平均・差分（Δ）テーブルが表示される
4. `is_outlier = true` のセルはアンバー色でハイライト表示される（⚠ アイコン付き）
5. 「閉じる」でダイアログを閉じる
