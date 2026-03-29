# infra/gcp-iam/roles.tf
# 1. Artifact Registry へのアクセス権限（イメージのプッシュ用）
resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 2. Cloud Run の管理者権限（デプロイ用）
resource "google_project_iam_member" "cloud_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# 3. サービスアカウントユーザー権限（Cloud Run 実行用 SA の指定に必要）
resource "google_project_iam_member" "iam_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}
