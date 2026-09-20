data "aws_caller_identity" "current" {}

data "aws_rds_cluster" "database" {
  cluster_identifier = var.db_cluster_identifier
}

data "aws_vpc" "default" {
  count = var.enable_vpc_connector && var.vpc_id == "" ? 1 : 0

  default = true
}

data "aws_vpc" "selected" {
  count = var.enable_vpc_connector && var.vpc_id != "" ? 1 : 0

  id = var.vpc_id
}

data "aws_subnets" "default" {
  count = var.enable_vpc_connector && length(var.vpc_subnet_ids) == 0 ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [local.connector_vpc_id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_db_subnet_group" "database" {
  count = var.enable_vpc_connector && try(data.aws_rds_cluster.database.db_subnet_group_name, null) != null && data.aws_rds_cluster.database.db_subnet_group_name != "" ? 1 : 0

  name = data.aws_rds_cluster.database.db_subnet_group_name
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

locals {
  connector_vpc_id = var.enable_vpc_connector ? (
    var.vpc_id != "" ? var.vpc_id : (
      length(data.aws_db_subnet_group.database) > 0 ? data.aws_db_subnet_group.database[0].vpc_id : data.aws_vpc.default[0].id
    )
  ) : null

  connector_subnet_ids = var.enable_vpc_connector ? (
    length(var.vpc_subnet_ids) > 0 ? var.vpc_subnet_ids : (
      length(data.aws_db_subnet_group.database) > 0 ? data.aws_db_subnet_group.database[0].subnet_ids : data.aws_subnets.default[0].ids
    )
  ) : []
}
