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
| 5 | `SPECIAL_EMPLOYMENT` | `special_employment_shifts: list[str]`（デフォルト: `["weekday_night"]`） | `is_special=true` のワーカーが許可外の枠にアサインされている | 可 |
| 8a | `NEW_HIRE_TENURE` | `hired_tenure_months: int`（デフォルト: 6） | `transfer_type=hired` のワーカーが `joined_at` から `hired_tenure_months` ヶ月未満 | 可 |
| 8b | `TRANSFER_TENURE` | `cross_division_transfer_tenure_months: int`（デフォルト: 3） | `transfer_type=transfer_in` かつ `is_cross_division_transfer=true` のワーカーが異動日から `cross_division_transfer_tenure_months` ヶ月未満 | 可 |

### 警告ルール（`severity: "warning"`）

| # | コード | 設定パラメータ | 内容 | オーバーライド |
|---|--------|----------------|------|---------------|
| W1 | `CONSECUTIVE_HOLIDAYS` | `avoid_consecutive_holidays: bool` | 同一ワーカーが連続する日に休日系スロットへアサインされている | ― |

> **注意**: `CONSECUTIVE_HOLIDAYS` はフロントエンドのみ実装。バックエンド保存時の検証対象外。

### 設定スキーマ（`ShiftRulesConfig`）

```
# backend: app/models/rule_schemas.py
# frontend: frontend/types/shiftRules.ts

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

ShiftWarningsConfig:
  avoid_consecutive_holidays: bool = True
```

> `target_departments` / `target_all_departments` はアサイン可能部門の絞り込みに使用。バックエンドの `_validate_worker_departments` で検証される（ビジネスルールとは独立した前提チェック）。
> `hired_tenure_months` / `cross_division_transfer_tenure_months` は `0` を指定すると制限なしとして扱う。

---

## 3. 実装ファイルマップ

| 役割 | ファイル |
|------|---------|
| バックエンド: ルールスキーマ定義 | `backend/app/models/rule_schemas.py` |
| バックエンド: ルール取得・更新サービス | `backend/app/services/shift_rules_service.py` |
| バックエンド: ルール適用バリデーター | `backend/app/services/shift_validation_service.py` |
| バックエンド: アサイン保存サービス（検証統合） | `backend/app/services/shift_assignment_service.py` |
| バックエンド: バリデーションコンテキストサービス | `backend/app/services/validation_context_service.py` |
| バックエンド: Rules API エンドポイント | `backend/app/routers/rules.py` |
| バックエンド: Shifts API エンドポイント | `backend/app/routers/shifts.py` |
| フロントエンド: ルール型定義・デフォルト値 | `frontend/types/shiftRules.ts` |
| フロントエンド: バリデーション純粋関数群 | `frontend/utils/shiftValidators.ts` |
| フロントエンド: バリデーション結果フック | `frontend/hooks/useShiftValidation.ts` |
| フロントエンド: ルール取得・更新フック | `frontend/hooks/useShiftRules.ts` |
| フロントエンド: バリデーションコンテキスト取得フック | `frontend/hooks/useValidationContext.ts` |
| バックエンド: バリデーションテスト | `backend/tests/unit/test_shift_validation_service.py` |
| バックエンド: ルールサービステスト | `backend/tests/unit/test_shift_rules_service.py` |

---

## 4. 月跨ぎ `min_interval_days` バリデーション

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

## 5. 新しいルールを追加するステップ

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

