# UX: 月ナビゲーション時にカレンダーが planLoading でちらつく

**種別**: UX 改善  
**優先度**: Medium  
**影響範囲**: `frontend/app/shift-requirements/page.tsx`

---

## 問題の概要

`page.tsx` の描画分岐は `isLoading || planLoading` をまとめてチェックしており、月ナビゲーション後に `useShiftPlan` の再フェッチが発生するたびに **カレンダー全体がローディング表示に切り替わります**。

```tsx
// 現在の実装（問題あり）
{isLoading || planLoading ? (
  <div>読み込み中...</div>
) : activeDept ? (
  <ShiftCalendar ... />
) : ...}
```

## 何が問題か

`isLoading`（部門・ルール）は初回のみ発生しますが、`planLoading`（過去プラン）は月を切り替えるたびに `true` になります。
結果として、月ナビゲーションのたびにカレンダーが消えて「読み込み中...」が表示され、UX が劣化します。

## 修正方法

`planLoading` を **カレンダーの表示制御から分離** し、カレンダー自体は継続表示しながらタブやデータの切り替えだけをローディング中として処理する。

```tsx
// 修正後
{isLoading ? (
  <div>読み込み中...</div>
) : activeDept ? (
  <>
    {/* 表示モード切り替えタブ */}
    {!planLoading && shiftPlan && (
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {/* タブ */}
      </div>
    )}
    {planLoading && (
      <div className="text-xs text-gray-400 mb-2">過去データを確認中...</div>
    )}
    <ShiftCalendar
      department={activeDept}
      pastPlan={effectiveMode === "past" ? shiftPlan : null}
      readOnly={effectiveMode === "past"}
      onYearMonthChange={handleYearMonthChange}
    />
  </>
) : ...}
```

## 補足

SWR は `keepPreviousData: true` オプションを使うことでフェッチ中も前のデータを保持できます。`useShiftPlan.ts` の SWR オプションに追加することも有効です。

```typescript
// useShiftPlan.ts
const { data, error, isLoading } = useSWR<ShiftPlanDetail | null>(
  swrKey,
  fetcher,
  {
    revalidateOnFocus: false,
    keepPreviousData: true, // 追加
  },
);
```

ただし `keepPreviousData` を使うと月切り替え直後に前月のデータが表示され続けるため、`page.tsx` 側で月変更直後に `viewMode` をリセットする既存のロジックとの組み合わせに注意が必要です。
