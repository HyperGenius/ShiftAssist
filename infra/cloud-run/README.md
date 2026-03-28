# ShiftAssist Backend Infrastructure (Cloud Run)

このディレクトリには、ShiftAssist の FastAPI バックエンドを Google Cloud Run にデプロイするための Terraform コードが含まれています。
再利用性を高めるため、共通リソース（モジュール）と環境ごとの設定（エンバイロメント）に分離した構成を採用しています。

## 📁 ディレクトリ構成

```text
infra/cloud-run/
├── modules/                   # 共通化されたTerraformモジュール
│   ├── base/                  # 基盤リソース（Artifact Registry等）
│   └── cloud-run/             # アプリケーション層（Cloud Run, IAM, Secret Manager）
└── environments/              # 環境ごとのデプロイ設定
    ├── prod/                  # 本番環境 (Production)
    └── (dev/)                 # ※必要に応じて追加可能
```

## 🛠️ 事前準備

デプロイを実行する前に、以下の準備が必要です。

1. **ツールのインストール**
   - [Terraform](https://developer.hashicorp.com/terraform/downloads) (>= 1.0)
   - [Google Cloud CLI (gcloud)](https://cloud.google.com/sdk/docs/install)

2. **GCP 認証**
   ```bash
   gcloud auth application-default login
   ```

3. **必要な認証情報・値の取得**
   - GCP プロジェクト ID
   - Neon Database の接続 URL (`postgresql://...`)
   - Clerk Secret Key (`sk_live_...` または `sk_test_...`)
   - Clerk JWKS URL

## 🚀 デプロイ手順（本番環境: prod の場合）

### 1. ディレクトリの移動
対象環境のディレクトリに移動します。

```bash
cd environments/prod
```

### 2. 変数ファイルの設定
サンプルの変数をコピーして、実際の値に書き換えます。

```bash
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` をエディタで開き、必要な値を設定してください。（※このファイルは `.gitignore` に含まれるため、Gitにはコミットされません）

### 3. 初期化 (init)
Terraform を初期化します。Stateファイルを保存する GCS バケット名を指定してください。

```bash
terraform init -backend-config="bucket=<YOUR_GCS_BUCKET_NAME>"
```

### 4. 計画の確認 (plan)
どのようなリソースが作成・変更されるかを確認します。

```bash
terraform plan
```

### 5. デプロイの実行 (apply)
変更を適用し、リソースを作成します。

```bash
terraform apply
```
完了すると、Cloud RunのURLやArtifact RegistryのリポジトリURLが出力（Outputs）として表示されます。

---

## 💡 新しい環境（例: dev）を追加する方法

モジュール化されているため、新しい環境の追加は非常に簡単です。

1. `environments/prod` ディレクトリをコピーして `environments/dev` を作成します。
2. `environments/dev/versions.tf` を開き、バックエンドの prefix を変更します。
   ```hcl
   backend "gcs" {
     prefix = "terraform/cloud-run/dev" # prod から dev に変更
   }
   ```
3. `environments/dev/terraform.tfvars` の `environment` 変数や各種シークレットを開発環境用の値に変更します。
4. あとは同様に `terraform init`, `plan`, `apply` を実行するだけです。

## 🔐 シークレットの管理について
本構成では、Secret Managerのリソース（枠組み）と IAM 権限の作成、および初期値の登録を Terraform で行っています。
GitHub Actions などの CI/CD パイプラインを構築する場合は、Terraform にはダミーの値を渡し、実際の最新シークレット値の更新は CI/CD 側、または手動で GCP コンソールから行う運用に切り替えることも検討してください。
