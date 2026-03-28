
## Setup Neon Database with Terraform

`infra/neon/` 配下の Terraform コードを使って、Neon 上にプロジェクト・データベース・ロール（DBユーザー）を作成します。

### 前提条件

* [Terraform](https://developer.hashicorp.com/terraform/install) `>= 1.0` がインストール済みであること
* [Neon](https://neon.tech) アカウントを作成し、以下の2つの値を取得済みであること
  * **API キー**: Neon コンソール → Account Settings → API Keys → **Generate new API key**
  * **Organization ID**: Neon コンソール → Organization Settings → ページ上部に表示される `org_XXXXXXXX` 形式の ID

### 手順

#### 1. ディレクトリに移動

```bash
cd infra/neon
```

#### 2. 環境変数で API キーと Organization ID をセット

Neon の認証情報をシェルの環境変数に設定します（ファイルに書き出さないことで、誤コミットを防ぎます）。

```bash
export TF_VAR_neon_api_key="<YOUR_NEON_API_KEY>"
export TF_VAR_neon_org_id="<YOUR_NEON_ORG_ID>"   # 例: org_XXXXXXXXXXXXXXXX
```

#### 3. Terraform の初期化

プロバイダー (`kislerdm/neon`) をダウンロードします。

```bash
terraform init
```

#### 4. 実行計画の確認

作成されるリソース（プロジェクト・ロール・データベース）を事前に確認します。

```bash
terraform plan
```

#### 5. リソースの作成

問題がなければ `apply` を実行します。確認プロンプトに `yes` と入力してください。

```bash
terraform apply
```

以下の3リソースが作成されます。

| リソース | 内容 |
|---|---|
| `neon_project.this` | Neon プロジェクト (`ShiftAssist`) |
| `neon_role.owner` | DB ロール (`shift_assist_owner`) |
| `neon_database.main` | データベース (`shift_assist_db`) |

#### 6. 接続文字列の取得

`apply` 完了後、以下のコマンドで接続文字列 (`DATABASE_URL`) を取得できます。
パスワードを含む機密情報のため、`-raw` フラグで平文出力します。

```bash
terraform output -raw database_url
```

出力された接続文字列をバックエンドの `.env` ファイルに設定してください。

```env
DATABASE_URL="postgresql://shift_assist_owner:<password>@<host>/shift_assist_db?sslmode=require"
```

### リソースの削除

検証用に作成したリソースを削除する場合は以下を実行します。

> **注意**: データベースのデータもすべて削除されます。本番環境では実行しないでください。

```bash
terraform destroy
```
