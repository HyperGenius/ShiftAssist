# シフトカレンダー UX 改善

## 概要

シフトカレンダーのアサイン操作全体の UX を改善する。

## 実装内容

### 1. 対応者リストのビジュアル統一

**変更ファイル:** `WorkerListPanel.tsx`

- 全表示モード（`showAll = true`）・スマートサジェストモード（`showAll = false`）ともに `SmartSuggestRow` を使用し、6カラムGrid表示に統一
- 全表示モードでも制約外のWorkerには `disabled` スタイル（グレーアウト）を適用
- グリッドヘッダーをどちらのモードでも表示（`activeSlotType` が設定されている場合）
- `WorkerListPanel` から未使用の `WorkerCard` import を削除

### 2. D&D アサイン精度の改善

#### 2-1. ドラッグオーバーレイのコンパクト化

**変更ファイル:** `ShiftCalendar.tsx`

- `DragOverlay` の内容を Worker 名のみ表示するコンパクトラベルに変更（`max-w-[120px]`）
- 所属バッジ等を非表示にすることでラベル幅を縮小し、当たり判定を直感的に改善

#### 2-2. アサイン済みスロットへの上書き禁止と赤ハイライト

**変更ファイル:** `ShiftSlotDropZone.tsx`, `ShiftCalendar.tsx`

- `ShiftSlotDropZone` でアサイン済みスロット（`workerId !== null`）へのドラッグ時に `isAllowed = false` として判定
- ドラッグ中にアサイン済みスロットへホバーすると `border-red-500 bg-red-50` で強調表示
- `handleDragEnd` でもアサイン済みスロットへのドロップを拒否（処理を中断）

### 3. クリックベースのアサイン方式の追加

**変更ファイル:** `ShiftCalendar.tsx`, `ShiftSlotDropZone.tsx`, `ShiftSlot.tsx`, `CalendarCell.tsx`, `WorkerListPanel.tsx`, `WorkerCard.tsx`, `SmartSuggestRow.tsx`

#### フロー
1. **ステップ 1:** 空きスロット（`workerId === null`）をクリック → そのスロットを「選択中」状態にする
2. **ステップ 2:** Worker リスト内の Worker をクリック → 選択中スロットに Worker をアサイン

#### 実装詳細
- `ShiftCalendar` に `selectedSlotKey: string | null` state を追加
- `handleSlotSelect(key: string)` コールバックで選択状態を管理（同じスロットを再クリックで解除）
- `handleClickAssign(workerId: string)` コールバックでアサイン処理（`handleDragEnd` と同等ロジック）
- 選択中スロットは `ring-2 ring-blue-500 ring-offset-1` で強調表示
- アサイン済みスロットをクリックしても選択状態にならない
- `WorkerListPanel` に「→ Workerをクリックしてアサイン」バナーを表示（選択中時のみ）
- `WorkerCard` / `SmartSuggestRow` に `onWorkerClick` prop 追加（クリック時にアサイン実行）
- `onWorkerClick` が設定されている場合、カーソルを `cursor-pointer` に変更し、hover 時に青系ハイライト
- 外部クリック（スロット・Worker 以外）で選択解除（外側 div の `onClick` ハンドラ）
- D&D ドラッグ開始時もクリックアサイン選択を解除

### 4. Worker リストのスクロール追従（Sticky 化）

**変更ファイル:** `ShiftCalendar.tsx`

- `sticky top-4` を `md:sticky md:top-4` に変更し、モバイル幅ではスティッキー挙動を無効化
- `h-[calc(100vh-8rem)]` と `WorkerListPanel` 内の `flex-1 overflow-auto` による内部スクロールはそのまま維持

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `ShiftCalendar.tsx` | `selectedSlotKey` state、クリックアサインハンドラ、D&D上書き禁止、DragOverlay コンパクト化、sticky 対応 |
| `ShiftSlotDropZone.tsx` | アサイン済みスロット上書き禁止・赤ハイライト、`isSelected` ring、`onSelectSlot` callback |
| `ShiftSlot.tsx` | `selectedSlotKey` / `onSlotSelect` props パススルー、`buildDropZoneId` import |
| `CalendarCell.tsx` | `selectedSlotKey` / `onSlotSelect` props パススルー |
| `WorkerListPanel.tsx` | 全表示モードを SmartSuggestRow に統一、クリックアサインバナー、`onWorkerClick` 追加 |
| `WorkerCard.tsx` | `onWorkerClick` prop、クリック時アサイン対応 |
| `SmartSuggestRow.tsx` | `onWorkerClick` prop、クリック時アサイン対応 |
