# シフトカレンダー年月ナビゲーション改善仕様書

## 1. 背景・目的

シフト枠カレンダーの年月移動を「前月」「翌月」ボタンの連打のみに依存していた従来の設計を改善し、以下の2点を実現する。

1. **URL 同期による状態永続化**: ページリロードやブラウザバック後も表示中の年月が保持される。
2. **年月ダイレクト選択機能**: ドロップダウンセレクターにより離れた月へ1回の操作で移動できる。

---

## 2. 解決する課題

| # | 課題 | 影響 |
|---|------|------|
| 1 | `useState` のみで年月を管理しているため、リロード・ブラウザバックで表示月が初期値（当月）にリセットされる | ユーザーが作業中の月に再アクセスするたびに操作が必要 |
| 2 | 離れた月を表示するには「前月」「翌月」ボタンを何度もクリックする必要がある | 操作コストが高く UX が低下する |

---

## 3. 実装方針

### 3.1 URL クエリパラメータによる年月の永続化

- `next/navigation` の `useSearchParams` と `useRouter` を使用する。
- URL フォーマット: `/shift-requirements?year=2026&month=7`
- `ShiftRequirementsPage` が URL から `year` / `month` を読み取り、`ShiftCalendar` へ props として渡す。
- 年月変更時は `router.replace` で URL を更新する（ブラウザ履歴を汚染しない）。
- パラメータが未指定または不正な場合は当月をデフォルト値として使用する。

### 3.2 年月ダイレクト選択セレクター（`YearMonthPicker`）

- `ShiftCalendar` のヘッダー中央部に2つのセレクトボックス（年・月）を配置する。
- 年の選択範囲: `現在年 − 1` ～ `現在年 + 2`（`yearRange` prop でカスタマイズ可能）
- 月の選択範囲: 1 〜 12 月
- 選択変更時に `onYearMonthChange(year, month)` を即時呼び出す。

---

## 4. コンポーネント設計

### 4.1 `YearMonthPicker` コンポーネント

**ファイル**: `frontend/components/shift-calendar/YearMonthPicker.tsx`

| Props | 型 | 説明 |
|-------|----|------|
| `year` | `number` | 現在表示中の年（制御値） |
| `month` | `number` | 現在表示中の月（制御値） |
| `onChange` | `(year: number, month: number) => void` | 年月変更コールバック |
| `yearRange` | `{ min: number; max: number }?` | 年セレクターの範囲（省略時: 現在年±1〜+2） |

### 4.2 `ShiftCalendar` コンポーネント（変更点）

**ファイル**: `frontend/components/shift-calendar/ShiftCalendar.tsx`

- `year` / `month` を内部 `useState` から **制御 props** に変更。
- `onYearMonthChange` を必須 props に変更（optional → required）。
- ヘッダー中央に `YearMonthPicker` を配置し、静的テキスト表示を置き換える。

### 4.3 `ShiftRequirementsPage`（変更点）

**ファイル**: `frontend/app/shift-requirements/page.tsx`

- `useSearchParams` を含む内部コンポーネント `ShiftRequirementsContent` を抽出し、`<Suspense>` でラップする。
- `calYear` / `calMonth` の状態管理を削除し、URL から直接読み取る形式に変更。
- `handleYearMonthChange` で `router.replace` により URL を更新する。
- `ShiftCalendar` へ `year` / `month` props を追加で渡す。

---

## 5. URL 設計

| パラメータ | 型 | 例 | 説明 |
|------------|----|----|------|
| `year` | 整数 | `2026` | 表示する年（1以上の正整数） |
| `month` | 整数 | `7` | 表示する月（1〜12） |

**例**: `/shift-requirements?year=2026&month=7`

不正値（範囲外・非数値）の場合は当月をデフォルトとして使用する。

---

## 6. 動作仕様

### 年月変更フロー

```
ユーザー操作
  ├── 「前月」ボタンクリック  ┐
  ├── 「翌月」ボタンクリック  ├─→ onYearMonthChange(y, m) → router.replace(?year=y&month=m)
  └── YearMonthPicker 選択   ┘
        ↓
  URL が更新される（ブラウザアドレスバーに反映）
        ↓
  useSearchParams が新しい値を検知
        ↓
  ShiftCalendar に新しい year/month が渡される
        ↓
  カレンダーが指定月を表示
```

### リロード時フロー

```
ブラウザリロード
  → URL: /shift-requirements?year=2026&month=7
  → useSearchParams が year=2026, month=7 を読み取る
  → ShiftCalendar が 2026年7月を表示（状態が復元される）
```

---

## 7. 実装ファイル一覧

| ファイル | 変更種別 | 概要 |
|----------|----------|------|
| `frontend/components/shift-calendar/YearMonthPicker.tsx` | 新規作成 | 年月ダイレクト選択コンポーネント |
| `frontend/components/shift-calendar/ShiftCalendar.tsx` | 変更 | year/month を制御 props に変更、YearMonthPicker を組み込み |
| `frontend/app/shift-requirements/page.tsx` | 変更 | URL クエリパラメータとの同期、Suspense ラッパーの追加 |
| `docs/calendar-year-month-navigation-feature.md` | 新規作成 | 本仕様書 |
