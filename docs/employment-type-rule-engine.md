# 雇用形態別の柔軟なルールエンジン

## 概要

雇用形態（`EmploymentType`）ごとに「どの枠に入れるか」「回数制限の上書き」「ペア制限」などのルールを自由に設定・変更できる仕組みです。  
テナントごとの多様な雇用形態や労務規定に対し、ソースコードを修正することなく設定のみで柔軟に対応できます。

---

## 実装されたルール

### 1. ペア制限ルール（`require_default_pair`）

| 項目 | 内容 |
|------|------|
| 概要 | `require_default_pair=True` の雇用形態を持つWorkerをアサインする際、ペア相手にデフォルト雇用形態（`is_default=True`）のWorkerが必須かどうかを制御する |
| 例 | 「延長雇用」の雇用形態のWorker同士でペアを組むことは不可 |
| スキップ条件 | `workers_per_slot=1`（1人枠）の場合はこのチェックをスキップ |
| 違反コード | `EMPLOYMENT_PAIR_RESTRICTION` |
| severity | `error` |

### 2. アサイン可能枠の制限（`allowed_slot_types`）

| 項目 | 内容 |
|------|------|
| 概要 | 雇用形態ごとにアサイン可能な `SlotTypeEnum` を明示的にリストで管理できる |
| フォールバック | リストが空（または `null`）の場合は、グローバルの `ShiftRulesConfig.special_employment_shifts` にフォールバック |
| 後方互換性 | グローバルの `special_employment_shifts` による既存の動作は継続する |
| 違反コード | `SPECIAL_EMPLOYMENT`（既存コード継続使用） |
| severity | `error` |

#### SlotTypeEnum 一覧

| 値 | 日本語名 |
|----|---------|
| `weekday_night` | 平日夜間 |
| `sat_day` | 土曜昼間 |
| `sat_night` | 土曜夜間 |
| `sun_hol_day` | 日曜・祝日昼間 |
| `sun_hol_night` | 日曜・祝日夜間 |
| `long_hol_day` | 長期連休昼間 |
| `long_hol_night` | 長期連休夜間 |
| `sat_pre_hol_night` | 土曜・祝前日夜間 |

### 3. 年間シフト回数上限の上書き（`annual_limit_overrides`）

| 項目 | 内容 |
|------|------|
| 概要 | `AnnualShiftLimitsConfig` の各フィールドを雇用形態ごとに上書きできる |
| 各フィールドの動作 | `null` の場合はグローバルルール（`ShiftWarningsConfig.annual_shift_limits`）の値を使用 |
| `0` を指定した場合 | 制限なしとして扱う（既存の `AnnualShiftLimitsConfig` の挙動に準拠） |
| severity | `warning`（保存をブロックしない） |

#### 上書き対象フィールド

| フィールドキー | 違反コード | 説明 |
|--------------|-----------|------|
| `annual_total` | `ANNUAL_TOTAL_SHIFTS` | 全スロット合計 |
| `weekday_night` | `ANNUAL_WEEKDAY_NIGHT` | 平日夜間 |
| `sat_day` | `ANNUAL_SAT_DAY` | 土曜昼間 |
| `sat_night` | `ANNUAL_SAT_NIGHT` | 土曜夜間 |
| `sun_hol_day` | `ANNUAL_SUN_HOL_DAY` | 日祝昼間 |
| `sun_hol_night` | `ANNUAL_SUN_HOL_NIGHT` | 日祝夜間 |
| `sat_pre_hol_night` | `ANNUAL_SAT_PRE_HOL_NIGHT` | 土曜・祝前日夜間 |

---

## データモデル

### `employment_type_rules` テーブル

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | UUID (PK) | プライマリキー |
| `employment_type_id` | UUID (FK → `employment_types.id`) | 雇用形態ID（1対1） |
| `tenant_id` | String (インデックス付き) | テナントID |
| `require_default_pair` | Boolean (デフォルト `False`) | ペア制限フラグ |
| `allowed_slot_types` | JSON (`list[str]`、null許容) | アサイン可能な枠種別リスト |
| `annual_limit_overrides` | JSON (null許容) | 年間上限上書き設定 |
| `created_at` | DateTime | 作成日時 |
| `updated_at` | DateTime | 更新日時 |

**制約:** `employment_type_id` に `UniqueConstraint`（1対1）

---

## APIエンドポイント

すべてのエンドポイントは `X-Tenant-Id` ヘッダーによるテナントアイソレーションが必須です。

### `GET /api/employment-types/{employment_type_id}/rules`

指定した雇用形態のルール設定を取得します。  
ルールが未設定の場合はデフォルト値（制限なし）を返します。

**レスポンス例:**
```json
{
  "require_default_pair": false,
  "allowed_slot_types": ["weekday_night"],
  "annual_limit_overrides": {
    "annual_total": null,
    "weekday_night": 5,
    "sat_day": null,
    "sat_night": null,
    "sun_hol_day": null,
    "sun_hol_night": null,
    "sat_pre_hol_night": null
  }
}
```

### `PUT /api/employment-types/{employment_type_id}/rules`

指定した雇用形態のルール設定を更新（upsert）します。

**リクエストボディ例:**
```json
{
  "require_default_pair": true,
  "allowed_slot_types": ["weekday_night", "sat_day"],
  "annual_limit_overrides": {
    "weekday_night": 5
  }
}
```

---

## フロントエンド

### `EmploymentTypeRuleEditor` コンポーネント

`components/employment-types/EmploymentTypeRuleEditor.tsx`

雇用形態別ルールを設定・保存するUIコンポーネント。  
`EmploymentTypeSettingsForm` の雇用形態行から「ルール設定」ボタンで呼び出されます。

**機能:**
- `require_default_pair` トグル（チェックボックス）
- `allowed_slot_types` 複数選択（各 SlotTypeEnum をチェックボックスで表示）
- `annual_limit_overrides` 各フィールドの数値入力（空欄 = グローバルに従う、0 = 制限なし）

### 追加された型定義

`types/employmentType.ts`:
- `AnnualPartialLimitsConfig` — 年間上限の部分上書き設定
- `EmploymentTypeRuleConfig` — 雇用形態別ルール設定
- `EmploymentTypeRuleUpdate` — ルール更新リクエスト

### 追加されたフック関数

`hooks/useEmploymentTypes.ts`:
- `fetchEmploymentTypeRules(id)` — ルール設定を取得
- `updateEmploymentTypeRules(id, data)` — ルール設定を更新

---

## バリデーションロジック

`backend/app/services/shift_validation_service.py` に以下が追加・変更されています。

### 新規追加

- `_load_employment_type_rules(session, tenant_id)` — テナント内の全雇用形態ルールをキャッシュ取得
- `_check_employment_pair_restriction(...)` — ペア制限チェック（`EMPLOYMENT_PAIR_RESTRICTION`）

### 変更

- `_check_special_employment(...)` — 雇用形態別 `allowed_slot_types` があればグローバル設定より優先（後方互換性維持）
- `_check_annual_shift_limits(...)` — 雇用形態別 `annual_limit_overrides` を適用
- `validate_shift_assignments(...)` — 上記を組み込み、新ルールを実行

---

## グローバル設定との優先度

```
雇用形態別ルール（EmploymentTypeRule）
  ↓ 未設定の場合フォールバック
グローバルルール（ShiftRulesConfig / ShiftWarningsConfig）
```

- `allowed_slot_types` が `null` または空の場合 → `ShiftRulesConfig.special_employment_shifts` を使用
- `annual_limit_overrides` の各フィールドが `null` の場合 → `ShiftWarningsConfig.annual_shift_limits` の該当フィールドを使用

---

## 関連ファイル

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/models/models.py` | `EmploymentTypeRule` モデル追加 |
| `backend/app/models/rule_schemas.py` | `AnnualPartialLimitsConfig`、`EmploymentTypeRuleConfig` スキーマ追加 |
| `backend/app/models/schemas.py` | `EmploymentTypeResponse.rule` フィールド追加、`EmploymentTypeRuleUpdate` スキーマ追加 |
| `backend/app/services/employment_type_service.py` | `get_employment_type_rule`、`upsert_employment_type_rule` CRUD 追加 |
| `backend/app/services/shift_validation_service.py` | 新ルール追加・既存ルール拡張 |
| `backend/app/routers/employment_types.py` | `GET/PUT /rules` エンドポイント追加 |
| `backend/alembic/versions/p6q7r8s9t0u1_.py` | `employment_type_rules` テーブル作成マイグレーション |
| `backend/tests/unit/test_shift_validation_service.py` | 新ルールの単体テスト追加 |
| `frontend/types/employmentType.ts` | `EmploymentTypeRuleConfig`、`AnnualPartialLimitsConfig` 型追加 |
| `frontend/hooks/useEmploymentTypes.ts` | `fetchEmploymentTypeRules`、`updateEmploymentTypeRules` 追加 |
| `frontend/components/employment-types/EmploymentTypeRuleEditor.tsx` | 新規コンポーネント |
| `frontend/components/employment-types/EmploymentTypeSettingsForm.tsx` | ルールエディタ統合 |
