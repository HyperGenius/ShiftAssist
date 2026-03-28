variable "neon_api_key" {
  description = "Neon API Key"
  type        = string
  sensitive   = true
}

variable "neon_org_id" {
  description = "Neon Organization ID (found in Organization Settings)"
  type        = string
}

variable "project_name" {
  description = "Name of the Neon project"
  type        = string
  default     = "ShiftAssist"
}

variable "db_owner" {
  description = "Database owner username"
  type        = string
  default     = "shift_assist_owner"
}