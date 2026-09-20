resource "aws_security_group" "connector" {
  count = var.enable_vpc_connector ? 1 : 0

  name        = "${var.project_name}-connector-sg"
  description = "CloudMLOps App Runner VPC connector"
  vpc_id      = local.connector_vpc_id
}

resource "aws_security_group_rule" "rds_from_connector" {
  count = var.enable_vpc_connector && length(data.aws_rds_cluster.database.vpc_security_group_ids) > 0 ? 1 : 0

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = tolist(data.aws_rds_cluster.database.vpc_security_group_ids)[0]
  source_security_group_id = aws_security_group.connector[0].id
  description              = "PostgreSQL from App Runner VPC connector"
}

resource "aws_apprunner_vpc_connector" "main" {
  count = var.enable_vpc_connector ? 1 : 0

  vpc_connector_name = "${var.project_name}-connector"
  subnets            = slice(local.connector_subnet_ids, 0, min(2, length(local.connector_subnet_ids)))
  security_groups    = [aws_security_group.connector[0].id]
}

# Backend egress is VPC-only (for private RDS). Without a gateway endpoint, S3
# uploads would fail because these subnets typically have no NAT gateway.
data "aws_route_tables" "database_vpc" {
  count = var.enable_vpc_connector ? 1 : 0

  vpc_id = local.connector_vpc_id
}

resource "aws_vpc_endpoint" "s3" {
  count = var.enable_vpc_connector ? 1 : 0

  vpc_id            = local.connector_vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.database_vpc[0].ids
}
