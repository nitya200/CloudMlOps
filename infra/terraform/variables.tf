variable "aws_region" {
  description = "AWS region (must match ECR, RDS, and Secrets Manager)."
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Prefix for CloudMLOps AWS resource names."
  type        = string
  default     = "cloudmlops"
}

variable "github_repository" {
  description = "GitHub repo for OIDC trust (owner/name), e.g. nitya200/CloudMlOps."
  type        = string
}

variable "db_cluster_identifier" {
  description = "Existing RDS/Aurora cluster identifier."
  type        = string
  default     = "database-1"
}

variable "s3_bucket_name" {
  description = "Existing S3 bucket for document uploads."
  type        = string
}

variable "cors_origins" {
  description = "Comma-separated browser origins allowed to call the API."
  type        = string
  default     = "https://cloudmlops.netlify.app"
}

variable "backend_cpu" {
  description = "App Runner backend CPU (FLAN-T5 needs 2048 = 2 vCPU)."
  type        = string
  default     = "2048"
}

variable "backend_memory" {
  description = "App Runner backend memory in MB (4096 recommended for FLAN-T5)."
  type        = string
  default     = "4096"
}

variable "create_github_oidc_provider" {
  description = "Set false if token.actions.githubusercontent.com OIDC provider already exists."
  type        = bool
  default     = true
}

variable "create_iam_roles" {
  description = "Set false if AppRunnerECRAccessRole, CloudMLOpsInstanceRole, and GitHubActionsDeployRole already exist."
  type        = bool
  default     = false
}
