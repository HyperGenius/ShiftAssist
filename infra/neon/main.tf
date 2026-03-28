# プロジェクト作成
resource "neon_project" "this" {
  name                      = var.project_name
  org_id                    = var.neon_org_id
  history_retention_seconds = 0 # フリープランの上限エラーを回避
  region_id                 = "aws-ap-southeast-1"
}

# デフォルトブランチ (main) の取得

# ロール (DBユーザー) の作成
resource "neon_role" "owner" {
  project_id = neon_project.this.id
  branch_id  = neon_project.this.default_branch_id
  name       = var.db_owner
}

# データベースの作成
resource "neon_database" "main" {
  project_id = neon_project.this.id
  branch_id  = neon_project.this.default_branch_id
  name       = "shift_assist_db"
  owner_name = neon_role.owner.name
}