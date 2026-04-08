# Bug: React state updater 内でのサイドエフェクト呼び出し

**種別**: Bug  
**優先度**: High  
**影響範囲**: `frontend/components/shift-calendar/ShiftCalendar.tsx`

---

## 問題の概要

`ShiftCalendar.tsx` の `prevMonth` / `nextMonth` で、`setState` の関数型更新の **コールバック内** から `onYearMonthChange?.()` を呼び出しています。

```typescript
// 現在の実装（問題あり）
const prevMonth = useCallback(() => {
  if (month === 1) {
    setYear((y) => { onYearMonthChange?.(y - 1, 12); return y - 1; }); // ❌ サイドエフェクト
    setMonth(12);
  } else {
    setMonth((m) => { onYearMonthChange?.(year, m - 1); return m - 1; }); // ❌ サイドエフェクト
  }
}, [month, year, onYearMonthChange]);
```

## 何が問題か

React の `setState` 関数型更新コールバック（`(prev) => next` 形式）は **純粋関数** でなければなりません。副作用（外部関数の呼び出し・状態更新・API呼び出しなど）を含めることは React の仕様違反であり、以下のリスクがあります。

- **React 18 + Strict Mode** では state updater が開発環境で2回呼ばれるため、`onYearMonthChange` が2回実行される
- `onYearMonthChange` の中で `setCalYear` / `setCalMonth` / `setViewMode` が呼ばれるため、不整合な状態遷移が起きる可能性がある

## 修正方法

`onYearMonthChange` の呼び出しを state updater の **外** に移動する。

```typescript
// 修正後
const prevMonth = useCallback(() => {
  if (month === 1) {
    onYearMonthChange?.(year - 1, 12);
    setYear((y) => y - 1);
    setMonth(12);
  } else {
    onYearMonthChange?.(year, month - 1);
    setMonth((m) => m - 1);
  }
}, [month, year, onYearMonthChange]);

const nextMonth = useCallback(() => {
  if (month === 12) {
    onYearMonthChange?.(year + 1, 1);
    setYear((y) => y + 1);
    setMonth(1);
  } else {
    onYearMonthChange?.(year, month + 1);
    setMonth((m) => m + 1);
  }
}, [month, year, onYearMonthChange]);
```

## 影響

月ナビゲーション時に `page.tsx` 側の `calYear` / `calMonth` が2回更新されると、`useShiftPlan` の SWR フェッチも2回トリガーされ、不要なAPIリクエストが発生する。
