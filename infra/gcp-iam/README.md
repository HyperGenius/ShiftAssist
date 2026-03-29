# GCP IAM (Workload Identity Federation)

GitHub Actions から GCP へキーレス認証でアクセスするための IAM リソースを Terraform で管理します。

## 作成されるリソース

| リソース | 説明 |
|---|---|
| Workload Identity Pool | GitHub Actions の OIDC トークンを受け付けるプール |
| Workload Identity Provider | GitHub の OIDC issuer との紐付け・属性マッピング |
| Service Account | GitHub Actions がなりすますデプロイ用 SA |
| IAM Bindings | SA に付与するロール（Artifact Registry Writer / Cloud Run Admin / SA User） |

## 事前準備

```bash
PROJECT_ID=<YOUR_PROJECT_ID>>
gcloud auth application-default login
gcloud config set project ${PROJECT_ID}
```

## セットアップ手順

### 1. 変数ファイルの作成

```bash
cd infra/gcp-iam
cp terraform.tfvars.example terraform.tfvars
```

デフォルト値のままで問題ありません。

### 2. 初期化

```bash
BACKEND_BUCKET=${PROJECT_ID}-tfstate-prod
terraform init -backend-config="bucket=${BACKEND_BUCKET}"
```

### 3. 適用

```bash
terraform plan
terraform apply
```

### 4. GitHub Secrets への登録

apply 完了後に出力される値を GitHub リポジトリの **Settings → Secrets and variables → Actions** に登録します。

```bash
# 出力値の確認
terraform output workload_identity_provider_id
terraform output service_account_email
```

| GitHub Secret 名 | Terraform output |
|---|---|
| `WIF_PROVIDER` | `workload_identity_provider_id` |
| `WIF_SERVICE_ACCOUNT` | `service_account_email` |
| `GCP_PROJECT_ID` | `<YOUR_PROJECT_ID>>`（固定値） |

## 変数一覧

| 変数名 | デフォルト値 | 説明 |
|---|---|---|
| `project_id` | ― | GCP プロジェクト ID |
| `region` | `asia-northeast1` | リージョン |
| `github_repository` | ― | `オーナー/リポジトリ名` 形式 |
| `pool_id` | `github-actions-pool` | WIF プール ID |
| `provider_id` | `github-provider` | WIF プロバイダ ID |
| `service_account_id` | `github-actions-deployer` | サービスアカウント ID |

## 付与されるロール

| ロール | 用途 |
|---|---|
| `roles/artifactregistry.writer` | Docker イメージのプッシュ |
| `roles/run.admin` | Cloud Run サービスのデプロイ |
| `roles/iam.serviceAccountUser` | Cloud Run 実行用 SA の指定 |
