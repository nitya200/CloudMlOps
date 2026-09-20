data "aws_caller_identity" "current" {}

data "aws_rds_cluster" "database" {
  cluster_identifier = var.db_cluster_identifier
}

data "aws_db_subnet_group" "database" {
  name = data.aws_rds_cluster.database.db_subnet_group
}

data "aws_secretsmanager_secret" "database_url" {
  name = "${var.project_name}/database-url"
}

data "aws_secretsmanager_secret" "jwt_secret" {
  name = "${var.project_name}/jwt-secret"
}

data "aws_secretsmanager_secret" "admin_password" {
  name = "${var.project_name}/admin-password"
}

data "aws_ecr_repository" "backend" {
  name = "${var.project_name}-backend"
}

data "aws_ecr_repository" "frontend" {
  name = "${var.project_name}-frontend"
}

data "aws_iam_role" "ecr_access" {
  count = var.create_iam_roles ? 0 : 1
  name  = "AppRunnerECRAccessRole"
}

data "aws_iam_role" "instance" {
  count = var.create_iam_roles ? 0 : 1
  name  = "CloudMLOpsInstanceRole"
}

data "aws_iam_role" "github_deploy" {
  count = var.create_iam_roles ? 0 : 1
  name  = "GitHubActionsDeployRole"
}
