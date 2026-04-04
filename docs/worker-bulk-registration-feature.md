# Worker 一括登録機能 仕様書

## 概要

テナント管理者が JSON ファイルを用いて Worker（作業員）データを一括で登録・更新できる機能です。
アップロードされたデータ内にシステム未登録の「課（Department）」が含まれていた場合、エラーにせず自動的に課を新規登録します。

## API エンドポイント

### 差分プレビュー

```
POST /api/workers/bulk/preview
Header: X-Tenant-Id: <tenant_id>
```

**リクエストボディ:**
```json
{
  "workers": [
    {
      "employee_no": "EMP001",
      "name": "田中 太郎",
      "department_code": "dept_1",
      "department_name": "1課",
      "skill_rank_id": "<UUID>",
      "is_special": false,
      "joined_at": "2020-04-01"
    }
  ]
}
```

**レスポンス:**
```json
{
  "preview": [
    {
      "employee_no": "EMP001",
      "name": "田中 太郎",
      "department_code": "dept_1",
      "action": "create",
      "old_name": null,
      "department_is_new": false
    }
  ],
  "create_count": 1,
  "update_count": 0,
  "no_change_count": 0,
  "new_department_count": 0
}
```

`action` フィールドの値:
- `"create"`: 新規登録
- `"update"`: 既存データを上書き更新
- `"no_change"`: 変更なし

`department_is_new` が `true` の場合、その課コードは実行時に自動生成されます。

### 一括登録・更新実行

```
POST /api/workers/bulk
Header: X-Tenant-Id: <tenant_id>
```

**リクエストボディ:** プレビューと同一形式。

**レスポンス:**
```json
{
  "created": 3,
  "updated": 1,
  "departments_created": 1,
  "items": [...]
}
```

## バリデーション

- `employee_no` はリスト内で重複不可（HTTP 422 を返す）
- `skill_rank_id` は同一テナントに存在する必要がある（HTTP 404 を返す）
- 未登録の `department_code` は自動生成されるためエラーにならない

## DB 設計

### `workers` テーブルへの変更

`employee_no`（VARCHAR, NULL 許容）カラムを追加し、以下のユニーク制約を設定します。

```sql
UNIQUE (tenant_id, employee_no)
```

NULL は一意制約の対象外（PostgreSQL 標準動作）であるため、`employee_no` を持たない既存 Worker は制約の影響を受けません。

### アップサートキー

`employee_no` をキーとして既存 Worker の検索・更新を行います。一致する `employee_no` が存在しない場合は新規作成します。

## 処理フロー（バックエンド）

1. リクエストの重複 `employee_no` チェック
2. 指定された `skill_rank_id` がすべてテナント内に存在するか確認
3. データ内の `department_code` を抽出し、未登録のものを自動生成
4. 社員番号をキーに Worker を Upsert（新規作成 or 更新）
5. トランザクションをコミットし、処理結果を返却

## フロントエンド

### コンポーネント

`frontend/components/workers/WorkerBulkUploadPanel.tsx`

- ドラッグ＆ドロップ対応のファイルアップロードエリア
- JSON 形式検証（クライアントサイド）
- プレビュー表示（新規追加件数・更新件数・課の自動作成件数）
- 確認後に確定実行

`WorkerList.tsx` の「一括登録」ボタンからパネルを表示します。

### カスタムフック

`frontend/hooks/useWorkers.ts` に以下の関数を追加:

- `previewBulkUpload(payload)`: `POST /api/workers/bulk/preview` を呼び出し、差分プレビューを返す
- `bulkUploadWorkers(payload)`: `POST /api/workers/bulk` を呼び出し、一括登録・更新を実行。完了後に Worker 一覧キャッシュを無効化（再フェッチ）する

## JSON フォーマット例

```json
[
  {
    "employee_no": "EMP001",
    "name": "田中 太郎",
    "department_code": "dept_1",
    "department_name": "1課",
    "skill_rank_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "is_special": false,
    "joined_at": "2020-04-01"
  },
  {
    "employee_no": "EMP002",
    "name": "鈴木 花子",
    "department_code": "dept_new",
    "department_name": "新設課",
    "skill_rank_id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "is_special": false
  }
]
```

`department_name` は未指定の場合、`department_code` の値が課名として使用されます。
`joined_at` は省略可能です。

## セキュリティ（マルチテナント分離）

すべての操作において `X-Tenant-Id` ヘッダーを使用してデータを分離します。

- 課の自動生成時には `tenant_id` を付与
- Worker の作成・更新時には `tenant_id` を付与
- `skill_rank_id` の存在確認も `tenant_id` でフィルタリング

他テナントのデータに干渉しない設計となっています。
