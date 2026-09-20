resource "aws_security_group" "connector" {
  name        = "${var.project_name}-connector-sg"
  description = "CloudMLOps App Runner VPC connector"
  vpc_id      = data.aws_db_subnet_group.database.vpc_id
}

resource "aws_security_group_rule" "rds_from_connector" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = tolist(data.aws_rds_cluster.database.vpc_security_group_ids)[0]
  source_security_group_id = aws_security_group.connector.id
  description              = "PostgreSQL from App Runner VPC connector"
}

resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${var.project_name}-connector"
  subnets            = data.aws_db_subnet_group.database.subnet_ids
  security_groups    = [aws_security_group.connector.id]
}

# Backend egress is VPC-only (for private RDS). Without a gateway endpoint, S3
# uploads would fail because these subnets typically have no NAT gateway.
data "aws_route_tables" "database_vpc" {
  vpc_id = data.aws_db_subnet_group.database.vpc_id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_db_subnet_group.database.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.database_vpc.ids
}
