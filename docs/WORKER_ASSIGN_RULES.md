# 対応者アサインルールの管理手順 (WORKER_ASSIGN_RULES.md)

本ドキュメントは、ShiftAssistにおける「シフト作成ルール（対応者アサインルール）」の現状と、新しいルールを追加・変更する際の手順を定義したものです。

## 1. ルール検証の基本アーキテクチャ

ShiftAssistでは、ユーザー体験とデータ整合性を両立させるため、ルール検証を以下の2段階で行います。ルールを追加する際は、**必ず両方のシステムに実装を追加**する必要があります。

* **フロントエンド (Next.js)**: ユーザーの操作と同時にインメモリでアドホック計算を行い、エラーや警告を即座にUIに表示します。
* **バックエンド (FastAPI)**: シフトの確定（保存）リクエストを受け取った際、データベースの最新状態と照らし合わせて厳密な最終検証を行います。

本システムはSaaS構成であり、MVPフェーズではルールをデータベースのテーブルではなく **JSON形式のスキーマ定義** として管理しています。テナントごとのルール設定は `tenant_rules_config` テーブルに保存され、`GET /api/rules/` で取得、`PUT /api/rules/` で更新します。

### 手動オーバーライド (`is_manual_override`)

`severity: "error"` ルールも、アサイン保存リクエストに `is_manual_override: true` を付与することで強制保存が可能です。バックエンドはこのフラグが `true` の場合、ビジネスルール検証（`_validate_business_rules`）をスキップします。

---

## 2. 実装済みルール一覧

### エラールール（`severity: "error"`）

| # | コード | 設定パラメータ | 内容 | オーバーライド |
|---|--------|----------------|------|---------------|
| 1 | `DAILY_DUPLICATE` | ― | 同一ワーカーが同日に複数の枠にアサインされている | 可 |
| 2 | `SAME_DEPARTMENT` | `allow_same_department: bool` | 同一所属課のワーカーが同一枠にペアになっている | 可 |
| 3 | `SKILL_RANK_A` | `require_skill_ranks: list[str]` | 枠の全員がアサイン済みの際、`is_leader_eligible=true` のワーカーがいない | 可 |
| 4 | `WORK_INTERVAL` | `min_interval_days: int`（デフォルト: 10） | 同一ワーカーの別アサインとの間隔が `min_interval_days` 日未満（**月跨ぎ対応**） | 可 |
| C | `ASSIGN_PROHIBITED` | `CustomRule.is_assign_prohibited: bool` | カスタムルールの `is_assign_prohibited=true` が設定されたワーカーがいずれかの枠にアサインされている。`allowed_slot_types` より優先 | 可 |
| 5 | `SPECIAL_EMPLOYMENT` | `special_employment_shifts: list[str]`（デフォルト: `["weekday_night"]`） | `is_special=true` のワーカーが許可外の枠にアサインされている | 可 |
| 8a | `NEW_HIRE_TENURE` | `hired_tenure_months: int`（デフォルト: 6） | `transfer_type=hired` のワーカーが `joined_at` から `hired_tenure_months` ヶ月未満 | 可 |
| 8b | `TRANSFER_TENURE` | `cross_division_transfer_tenure_months: int`（デフォルト: 3） | `transfer_type=transfer_in` かつ `is_cross_division_transfer=true` のワーカーが異動日から `cross_division_transfer_tenure_months` ヶ月未満 | 可 |
| 11 | `TOTAL_AGE_LIMIT` | `max_total_age: int`（デフォルト: 120） | スロット内ワーカーの年齢合計（シフト日の月初時点）が `max_total_age` を超える。`0` で制限なし。`birth_date` が null のワーカーは除外（0歳扱い） | 可 |
| 12 | `NON_WEEKDAY_NIGHT_LIMIT` | `monthly_shift_limits.non_weekday_night: int`（デフォルト: 1） | 同一シフト計画期間内（月次）で、同一ワーカーが平日夜間以外スロット（`sat_day` / `sat_night` / `sun_hol_day` / `sun_hol_night` / `long_hol_day` / `long_hol_night` / `sat_pre_hol_night`）に `non_weekday_night` 回を超えてアサインされている。`0` で制限なし。`weekday_night` スロットには適用しない | 可 |
| 13 | `MONTHLY_TOTAL_LIMIT` | `monthly_shift_limits.monthly_total: int`（デフォルト: 2） | 同一シフト計画期間（月次）で、同一ワーカーの全スロット合計アサイン回数が上限を超えている。`0` で制限なし | 可 |
| 14 | `MONTHLY_WEEKDAY_NIGHT_LIMIT` | `monthly_shift_limits.weekday_night: int`（デフォルト: 2） | 同一シフト計画期間（月次）で、同一ワーカーの `weekday_night` スロットへのアサイン回数が上限を超えている。`0` で制限なし | 可 |

> **注意**: `ASSIGN_PROHIBITED` はカスタムルール（`custom_rules` テーブル）の `is_assign_prohibited` フィールドで制御する。グローバルルール（`ShiftRulesConfig`）の設定パラメータではない。

### 警告ルール（`severity: "warning"`）

| # | コード | 設定パラメータ | 内容 | オーバーライド |
|---|--------|----------------|------|---------------|
| W1 | `CONSECUTIVE_HOLIDAYS` | `avoid_consecutive_holidays: bool` | 同一ワーカーが連続する日に休日系スロットへアサインされている | ― |
| W2 | `ANNUAL_TOTAL_SHIFTS` | `annual_shift_limits.annual_total: int`（デフォルト: 22） | 年間総シフト回数が上限を超える | ― |
| W3 | `ANNUAL_WEEKDAY_NIGHT` | `annual_shift_limits.weekday_night: int`（デフォルト: 10） | 年間 `weekday_night` 回数が上限を超える | ― |
| W4 | `ANNUAL_SAT_PRE_HOL_NIGHT` | `annual_shift_limits.sat_pre_hol_night: int`（デフォルト: 4） | 年間 `sat_pre_hol_night` 回数が上限を超える | ― |
| W5 | `ANNUAL_SAT_DAY` | `annual_shift_limits.sat_day: int`（デフォルト: 3） | 年間 `sat_day` 回数が上限を超える | ― |
| W6 | `ANNUAL_SAT_NIGHT` | `annual_shift_limits.sat_night: int`（デフォルト: 3） | 年間 `sat_night` 回数が上限を超える | ― |
| W7 | `ANNUAL_SUN_HOL_DAY` | `annual_shift_limits.sun_hol_day: int`（デフォルト: 4） | 年間 `sun_hol_day`（`long_hol_day` を合算）回数が上限を超える | ― |
| W8 | `ANNUAL_SUN_HOL_NIGHT` | `annual_shift_limits.sun_hol_night: int`（デフォルト: 5） | 年間 `sun_hol_night`（`long_hol_night` を合算）回数が上限を超える | ― |

> **注意**: `CONSECUTIVE_HOLIDAYS` および `ANNUAL_*` はフロントエンドのみ実装。バックエンド保存時の検証対象外。
> ただし `ANNUAL_*` はバックエンドでも `warnings` として `validate_shift_assignments` から返される（保存はブロックしない）。
> 年間集計の基準期間: シフト日が属する月を含む直近12ヶ月（例: 2026年4月作成中 → 2025年5月〜2026年4月）。
> `0` を設定すると制限なし（無制限）として扱う。

### 設定スキーマ（`ShiftRulesConfig` / `ShiftWarningsConfig`）

```
# backend: app/models/rule_schemas.py
# frontend: frontend/types/shiftRules.ts

MonthlyShiftLimitsConfig:
  monthly_total: int = 2        # 全スロット合計の月間上限
  weekday_night: int = 2        # weekday_night の月間上限
  non_weekday_night: int = 1    # 平日夜間以外スロットの月間上限（旧 max_non_weekday_night_per_period）

ShiftRulesConfig:
  min_interval_days: int = 10
  require_skill_ranks: list[str] = ["rank_a"]
  allow_same_department: bool = False
  special_employment_shifts: list[str] = ["weekday_night"]
  workers_per_slot: int = 2
  target_departments: list[str] = []
  target_all_departments: bool = True
  hired_tenure_months: int = 6
  cross_division_transfer_tenure_months: int = 3
  max_total_age: int = 120
  monthly_shift_limits: MonthlyShiftLimitsConfig = MonthlyShiftLimitsConfig()

ShiftWarningsConfig:
  avoid_consecutive_holidays: bool = True
  annual_shift_limits: AnnualShiftLimitsConfig = AnnualShiftLimitsConfig()

AnnualShiftLimitsConfig:
  annual_total: int = 22
  weekday_night: int = 10
  sat_day: int = 3
  sat_night: int = 3
  sun_hol_day: int = 4   # long_hol_day の実績を合算
  sun_hol_night: int = 5  # long_hol_night の実績を合算
  sat_pre_hol_night: int = 4
```

> `target_departments` / `target_all_departments` はアサイン可能部門の絞り込みに使用。バックエンドの `_validate_worker_departments` で検証される（ビジネスルールとは独立した前提チェック）。
> `hired_tenure_months` / `cross_division_transfer_tenure_months` は `0` を指定すると制限なしとして扱う。
> `monthly_shift_limits` の各フィールドも `0` を指定すると制限なしとして扱う。
> 旧フィールド `max_non_weekday_night_per_period` を含む DB レコードは、Pydantic の `@model_validator(mode="before")` により自動的に `monthly_shift_limits.non_weekday_night` へ移行される（後方互換）。

---

## 3. シフト枠種別（SlotTypeEnum）

| 値 | 意味 | 備考 |
|---|---|---|
| `weekday_night` | 平日夜間 | 特別雇用者も参加可（デフォルト） |
| `sat_day` | 土曜昼間 | |
| `sat_night` | 土曜夜間 | |
| `sun_hol_day` | 日曜・祝日昼間 | 月1回制限あり |
| `sun_hol_night` | 日曜・祝日夜間 | |
| `long_hol_day` | 長期連休昼間 | 集計時は `sun_hol_day` に合算 |
| `long_hol_night` | 長期連休夜間 | 集計時は `sun_hol_night` に合算 |
| `sat_pre_hol_night` | 土曜・祝前日夜間 | 金曜日または翌日が祝日となる平日の夜間 |

### `sat_pre_hol_night` の判定ロジック

「土曜・祝前日」とは以下の条件をすべて満たす日を指す。

1. 対象日の翌日が**土曜日または祝日**である
2. 対象日自身が**土曜日・日曜日・祝日でない**（平日だけが対象）

バックエンドでは `tenant_holidays` テーブルの祝日データを使用して判定する。フロントエンドでは `isSatPreHolidayDate` ユーティリティ（`frontend/utils/calendarUtils.ts`）を使用する。

---

## 4. 実装ファイルマップ

| 役割 | ファイル |
|------|---------|
| バックエンド: ルールスキーマ定義 | `backend/app/models/rule_schemas.py` |
| バックエンド: ルール取得・更新サービス | `backend/app/services/shift_rules_service.py` |
| バックエンド: ルール適用バリデーター | `backend/app/services/shift_validation_service.py` |
| バックエンド: アサイン保存サービス（検証統合） | `backend/app/services/shift_assignment_service.py` |
| バックエンド: バリデーションコンテキストサービス | `backend/app/services/validation_context_service.py` |
| バックエンド: Rules API エンドポイント | `backend/app/routers/rules.py` |
| バックエンド: Shifts API エンドポイント | `backend/app/routers/shifts.py` |
| バックエンド: シフト要件生成サービス | `backend/app/services/shift_requirement_service.py` |
| フロントエンド: ルール型定義・デフォルト値 | `frontend/types/shiftRules.ts` |
| フロントエンド: バリデーション純粋関数群 | `frontend/utils/shiftValidators.ts` |
| フロントエンド: カレンダーユーティリティ（sat_pre_hol判定含む） | `frontend/utils/calendarUtils.ts` |
| フロントエンド: バリデーション結果フック | `frontend/hooks/useShiftValidation.ts` |
| フロントエンド: ルール取得・更新フック | `frontend/hooks/useShiftRules.ts` |
| フロントエンド: バリデーションコンテキスト取得フック | `frontend/hooks/useValidationContext.ts` |
| フロントエンド: スマートサジェストフック（フィルタリング） | `frontend/hooks/useAvailableWorkers.ts` |
| フロントエンド: スマートサジェスト行コンポーネント（6カラムGrid） | `frontend/components/shift-calendar/SmartSuggestRow.tsx` |
| フロントエンド: 対応者リストパネル（スマートソート・集計連携） | `frontend/components/shift-calendar/WorkerListPanel.tsx` |
| フロントエンド: ルール設定フォーム | `frontend/components/rules/RulesSettingsForm.tsx` |
| フロントエンド: タブ切り替えクライアントコンポーネント | `frontend/components/rules/RulesTabsClient.tsx` |
| フロントエンド: 月間シフト回数上限設定タブ | `frontend/components/rules/MonthlyShiftLimitsTab.tsx` |
| バックエンド: バリデーションテスト | `backend/tests/unit/test_shift_validation_service.py` |
| バックエンド: ルールサービステスト | `backend/tests/unit/test_shift_rules_service.py` |
| バックエンド: シフト要件テスト | `backend/tests/unit/test_shift_requirement_service.py` |

---

## 5. 月跨ぎ `min_interval_days` バリデーション

### 概要

`WORK_INTERVAL` ルールの検証が月次プラン（`ShiftPlan`）単位に限定されていた問題を解消し、月跨ぎのアサイン（例: 3月31日と4月1日）でも正確に間隔チェックが機能するよう拡張しました。

### バックエンドの動作

`_check_work_interval`（`shift_validation_service.py`）は以下の順序で検証します:

1. **同月内チェック**: `ShiftRequirementAssignment` → `ShiftRequirement` のJOINクエリで `shift_date` が `[対象日 - min_interval_days, 対象日 + min_interval_days]` の範囲にある割り当てを検索。
2. **月跨ぎチェック**: `ShiftAssignment` → `ShiftSlot` → `ShiftPlan` のJOINクエリで、`ShiftPlan.status == 'published'`（確定済み）かつ日付が範囲内のスロットを検索。
   - **前月のシフトが `draft` 状態（未確定）の場合は対象外**となるため、月跨ぎ警告は出ない。

`ShiftSlot.date` には複合インデックス `ix_shift_slots_tenant_date (tenant_id, date)` が貼られており、`BETWEEN` クエリを効率的に実行できる。

### バリデーションコンテキスト API

`GET /api/shifts/validation-context` に `start_date`（YYYY-MM-DD形式）クエリパラメータを追加しました。

```
GET /api/shifts/validation-context?target_year_month=2026-04&start_date=2026-03-22
```

- `start_date` を指定すると、その日付以降の直近シフト日付を集計に含める。
- フロントエンドは `start_date = 月初日 - (min_interval_days - 1)` として送信することを推奨。

### フロントエンドの動作

`ShiftCalendar` コンポーネントは:

1. `useShiftRules()` でテナント設定のルール（`min_interval_days` 等）を取得。
2. `useValidationContext(targetYearMonth, validationStartDate)` で前月バッファを含むワーカー統計を取得。`validationStartDate = 月初日 - (min_interval_days - 1)`。
3. `useShiftValidation(calendarState, workers, rules.shift_rules, skillRanks, workerStats)` に `workerStats` を渡す。
4. `validateWorkInterval` が `calendarState`（当月）と `prevMonthDatesByWorker`（前月の `last_shift_date`）の両方を参照して間隔を計算する。

---

## 6. 新しいルールを追加するステップ

### Step 1: ルールスキーマ（JSON定義）の拡張

テナントごとに保持しているルール定義に、新しいルールの設定項目を追加します。

1. **バックエンドの型定義**: `backend/app/models/rule_schemas.py` の `ShiftRulesConfig`（またはエラールール非対象なら `ShiftWarningsConfig`）に新しいフィールドを追加します。
2. **フロントエンドの型定義**: `frontend/types/shiftRules.ts` の `ShiftRulesConfig`（または `ShiftWarningsConfig`）に対応するプロパティを追加します。また `DEFAULT_SHIFT_RULES` のデフォルト値も更新します。

### Step 2: フロントエンドのバリデーション実装

1. **純粋関数の追加**: `frontend/utils/shiftValidators.ts` に `validate<RuleName>` 関数を追加します。
2. **集約関数への組み込み**: 同ファイルの `validateSlot` 関数のリターン配列に追加した関数の呼び出しを追記します。
3. **UIへの反映**: `useShiftValidation` フック（`frontend/hooks/useShiftValidation.ts`）が `validateSlot` を呼ぶ構成のため、フックの変更は不要です。バリデーション結果は `ValidationMap` として各スロットに反映されます。
4. **手動オーバーライドの考慮**: `severity: "error"` か `severity: "warning"` かを判断します。`warning` の場合は保存ブロックのないUI表示のみで構いません。

### Step 3: バックエンドのバリデーション実装

1. **プライベート関数の追加**: `backend/app/services/shift_validation_service.py` に `_check_<rule_name>` 関数を追加します。
2. **集約関数への組み込み**: 同ファイルの `validate_shift_assignments` 関数のリターンリストに追加した関数の呼び出しを追記します。
3. **不正なリクエストのブロック**: `is_manual_override=False` かつエラー違反がある場合、`shift_assignment_service._validate_business_rules` が `400 Bad Request` を返す構成になっています（変更不要）。

### Step 4: テストの作成と実行

1. **バックエンド (Unit Testing)**: `backend/tests/unit/test_shift_validation_service.py` に以下のパターンのテストケースを追加します。
   * ルールを満たしている正常系
   * ルールに違反している異常系
   * オーバーライド可能なルールの場合、`is_manual_override=True` で強制保存するパターン
2. **フロントエンド**: 現時点でE2Eテスト（Playwright）は未整備です。追加する場合は `frontend/e2e/` ディレクトリを作成してください。

---

## 7. スマートサジェスト高度化（6カラムGrid・スマートソート・集計連携）

### 概要

シフト枠選択時の対応者リストを刷新し、6カラムGridレイアウト・スマートソート・集計データ警告を実装した。

### 7.1. 6カラムGridレイアウト（SmartSuggestRow）

`frontend/components/shift-calendar/SmartSuggestRow.tsx` が対応者1行を担当する。

| カラム | 幅 | 内容 |
|-------|-----|------|
| 1 | 18px | リーダーバッジ（`is_leader_eligible=true` の場合「L」を表示、ない場合も領域確保） |
| 2 | 20px | 雇用形態バッジ（`is_non_default_employment=true` の場合、雇用形態名先頭2文字を表示） |
| 3 | 1fr | 氏名（はみ出しは `truncate`） |
| 4 | 60px | 所属課名 |
| 5 | 60px | 役職名（`position_id` に紐づく名称） |
| 6 | 76px | 集計情報（`回数(月平均/月)` 形式、データなしは「—」） |

バッジがない場合も `inline-block` スペーサーで領域を確保し、垂直方向のラインを揃える。

### 7.2. スマートソートロジック

`WorkerListPanel` 内の `sortedAvailableWorkers` が以下の優先順位でソートを実施する。

1. **リーダー優先度**: 選択中の枠にすでにリーダー（`is_leader_eligible=true`）が1名以上いる場合、他のリーダー適性者を最下位に移動する。
2. **勤務平準化**: 過去12ヶ月の対象スロット種別の `monthly_avg`（月平均回数）が**少ない者**を上位に表示する。集計データが存在しないワーカーは `0` として扱う。
3. **フォールバック**: 月平均が同値の場合、所属課名順 → 氏名順（ともに日本語ロケール比較）。

### 7.3. 集計データ未計算時の警告

`aggregateStats` が未取得（`null`）またはアイテムが空の場合、リスト上部に警告バナーを表示する。

```
⚠️ 集計データが最新ではありません。[シフト集計ページ]で再計算してください
```

カレンダー画面では計算処理を行わず、集計ページ（`/admin/aggregate-stats`）への導線のみ提供する。

### 7.4. データフロー

```
ShiftCalendar
  ├─ useAggregateStats(targetYearMonth)  ← GET /api/tenants/{id}/worker-stats/aggregate
  ├─ useEmploymentTypes()                ← GET /api/employment-types/
  └─ WorkerListPanel (aggregateStats, employmentTypes)
       └─ SmartSuggestRow × n  (positionName, employmentTypeName, isNonDefaultEmployment, slotStats)
```

集計データの `AggregateWorkerStats` には `position_name`・`department_name`・`is_non_default_employment`・`employment_type_name`・`slot_stats` が含まれており、バックエンドの Eager Loading によって効率的に取得される。
