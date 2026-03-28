# infra/modules/base/main.tf
# Artifact Registry リポジトリ
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker repository for ${var.environment} environment"
  format        = "DOCKER"

  labels = {
    environment = var.environment
    project     = "ShiftAssist"
  }
}