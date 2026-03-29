# infra/modules/base/main.tf

# 必要なAPIの有効化
resource "google_project_service" "required_apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
  ])

  project                    = var.project_id
  service                    = each.key
  disable_on_destroy         = false
  disable_dependent_services = false
}

# Artifact Registry リポジトリ
resource "google_artifact_registry_repository" "main" {
  depends_on = [google_project_service.required_apis]
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for ${var.environment} environment"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    project     = "shiftassist"
  }
}