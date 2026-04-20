# カスタムシフトルール仕様書

## 概要

カスタムシフトルール（`CustomRule`）は、特定のワーカーに対してグローバルルールとは異なるシフト制約を個別に設定する機能です。テナントが `custom_rules` テーブルで管理するルール定義であり、ワーカーに `custom_rule_id` で紐付けて使用します。

---

## 1. データモデル

### `custom_rules` テーブル

| カラム名 | 型 | デフォルト | 説明 |
|---------|---|-----------|------|
| `id` | UUID | — | プライマリキー |
| `tenant_id` | String | — | テナントID（インデックス付き） |
| `name` | String | — | ルール名（テナント内で一意） |
| `allowed_slot_types` | JSON / null | null | アサイン可能な枠種別リスト。null または空は制限なし |
| `annual_limit_overrides` | JSON / null | null | 年間シフト回数上限の上書き設定（部分的に指定可） |
| `is_assign_prohibited` | Boolean | `false` | アサイン不可フラグ。`true` の場合は全枠アサイン禁止 |
| `created_at` | DateTime | — | レコード作成日時 |
| `updated_at` | DateTime | — | レコード最終更新日時 |

### `workers` テーブル（関連カラム）

| カラム名 | 型 | 説明 |
|---------|---|------|
| `custom_rule_id` | UUID / null | 紐付けるカスタムルールのID（`ON DELETE SET NULL`） |

---

## 2. 適用優先順位

カスタムルールと雇用形態ルールの適用優先順位は以下の通りです。

```
カスタムルール (is_assign_prohibited) > カスタムルール (allowed_slot_types) > 雇用形態別ルール > グローバルルール
```

### `is_assign_prohibited=true` の挙動

- `allowed_slot_types` の設定に関わらず、全スロットへのアサインが禁止される。
- `SPECIAL_EMPLOYMENT` チェックはスキップされ、`ASSIGN_PROHIBITED` エラーが返される。
- スマートサジェスト（WorkerListPanel）から非表示になる。

---

## 3. バリデーションルール: `ASSIGN_PROHIBITED`

### 仕様

| 項目 | 値 |
|-----|---|
| コード | `ASSIGN_PROHIBITED` |
| severity | `error` |
| オーバーライド | 可（`is_manual_override=true` で強制保存） |

### バックエンド実装

`backend/app/services/shift_validation_service.py` の `_check_assign_prohibited` 関数:

```python
def _check_assign_prohibited(
    workers: list[Worker],
    worker_custom_rules: dict[uuid.UUID, CustomRule | None] | None = None,
) -> list[ValidationViolationItem]:
    """カスタムルール: アサイン不可チェック."""
```

`validate_shift_assignments` の violations 集約では `_check_assign_prohibited` を `_check_special_employment` より前に呼び出す。

### フロントエンド実装

`frontend/utils/shiftValidators.ts` の `validateAssignProhibited` 関数:

```typescript
export function validateAssignProhibited(
  workers: readonly (string | null)[],
  workerMap: Map<string, Worker>,
  customRuleMap?: Map<string, { is_assign_prohibited?: boolean; ... }>,
): ValidationViolation[]
```

`validateSlot` の返却配列に `...validateAssignProhibited(...)` を `validateSpecialEmployment` より前に追加。

---

## 4. スマートサジェストからの除外

`useAvailableWorkers` フックは `customRules` パラメータを受け取り、`is_assign_prohibited=true` のワーカーをフィルタ先頭で除外する。

```typescript
// is_assign_prohibited=true のWorkerを最初に除外
if (customRuleMap && w.custom_rule_id) {
  const customRule = customRuleMap.get(w.custom_rule_id);
  if (customRule?.is_assign_prohibited) return false;
}
```

---

## 5. CustomRulesManager UI

### トグルスイッチ「アサイン不可」

- ルール作成・編集フォームに「アサイン不可（全枠へのアサインを禁止する）」トグル（チェックボックス）を追加。
- `is_assign_prohibited=true` の場合、`allowed_slot_types` チェックボックスを `disabled` にする（排他制御）。

### バッジ表示

- ルール一覧カードで `is_assign_prohibited=true` の場合、ルール名の右に「アサイン不可」バッジ（赤色）を表示。

---

## 6. Alembic マイグレーション

マイグレーションファイル: `backend/alembic/versions/r8s9t0u1v2w3_.py`

```python
op.add_column(
    "custom_rules",
    sa.Column(
        "is_assign_prohibited",
        sa.Boolean(),
        nullable=False,
        server_default="false",
    ),
)
```

既存レコードへの影響: `server_default="false"` により、既存の全 `custom_rules` レコードの `is_assign_prohibited` は `false` になる。

---

## 7. API スキーマ

### `CustomRuleCreate`（作成リクエスト）

```json
{
  "name": "ルール名",
  "is_assign_prohibited": true,
  "allowed_slot_types": null,
  "annual_limit_overrides": null
}
```

### `CustomRuleUpdate`（更新リクエスト）

```json
{
  "is_assign_prohibited": true
}
```

### `CustomRuleResponse`（レスポンス）

```json
{
  "id": "uuid",
  "tenant_id": "org_xxx",
  "name": "ルール名",
  "is_assign_prohibited": true,
  "allowed_slot_types": null,
  "annual_limit_overrides": null,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

---

## 8. 関連ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/models/models.py` | `CustomRule` クラスに `is_assign_prohibited` カラム追加 |
| `backend/app/models/schemas.py` | 各スキーマに `is_assign_prohibited` フィールド追加 |
| `backend/alembic/versions/r8s9t0u1v2w3_.py` | マイグレーション新規作成 |
| `backend/app/services/shift_validation_service.py` | `_check_assign_prohibited` 追加、`_check_special_employment` に skip 処理追加 |
| `backend/tests/unit/test_shift_validation_service.py` | `ASSIGN_PROHIBITED` テストケース追加 |
| `backend/tests/unit/test_custom_rule_service.py` | `_make_custom_rule` に `is_assign_prohibited` 追加 |
| `frontend/types/customRule.ts` | 型定義に `is_assign_prohibited` 追加 |
| `frontend/utils/shiftValidators.ts` | `ASSIGN_PROHIBITED` コード追加、`validateAssignProhibited` 関数追加 |
| `frontend/hooks/useAvailableWorkers.ts` | `customRules` パラメータ追加、除外ロジック追加 |
| `frontend/components/shift-calendar/WorkerListPanel.tsx` | `useCustomRules()` 呼び出し追加 |
| `frontend/components/shift-calendar/ShiftCalendar.tsx` | `useAvailableWorkers` に `customRules` を渡す |
| `frontend/components/rules/CustomRulesManager.tsx` | トグル追加、バッジ表示、グレーアウト制御 |
| `docs/WORKER_ASSIGN_RULES.md` | `ASSIGN_PROHIBITED` ルール追記 |
