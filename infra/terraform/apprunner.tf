resource "aws_apprunner_auto_scaling_configuration_version" "backend" {
  auto_scaling_configuration_name = "${var.project_name}-backend-scaling"
  max_concurrency                 = 4
  min_size                        = 1
  max_size                        = 4
}

resource "aws_apprunner_service" "backend" {
  service_name = "${var.project_name}-backend"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = local.ecr_access_role_arn
    }

    image_repository {
      image_identifier      = "${data.aws_ecr_repository.backend.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"

        runtime_environment_variables = {
          ENVIRONMENT         = "production"
          LOG_JSON            = "true"
          LOG_LEVEL           = "INFO"
          AUTO_CREATE_SCHEMA  = "false"
          RUN_MIGRATIONS      = "true"
          DATABASE_IAM_AUTH   = "true"
          AWS_REGION          = var.aws_region
          # FLAN-T5 on CPU (2 vCPU / 4 GB). CI bakes weights with INSTALL_AI=true + PREFETCH_MODEL=true.
          AI_BACKEND          = "flan-t5"
          AI_MODEL_NAME       = "google/flan-t5-small"
          AI_EAGER_LOAD       = "true"
          MAX_UPLOAD_SIZE_MB  = "10"
          STORAGE_BACKEND     = "s3"
          S3_BUCKET           = var.s3_bucket_name
          S3_PREFIX           = "documents"
          S3_REGION           = var.aws_region
          SEED_ADMIN          = "true"
          ADMIN_EMAIL         = "admin@cloudmlops.app"
          CORS_ORIGINS        = var.cors_origins
        }

        runtime_environment_secrets = {
          DATABASE_URL     = data.aws_secretsmanager_secret.database_url.arn
          JWT_SECRET_KEY   = data.aws_secretsmanager_secret.jwt_secret.arn
          ADMIN_PASSWORD   = data.aws_secretsmanager_secret.admin_password.arn
        }
      }
    }
  }

  instance_configuration {
    cpu               = var.backend_cpu
    memory            = var.backend_memory
    instance_role_arn = local.instance_role_arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  dynamic "network_configuration" {
    for_each = var.enable_vpc_connector ? [1] : []
    content {
      egress_configuration {
        egress_type       = "VPC"
        vpc_connector_arn = aws_apprunner_vpc_connector.main[0].arn
      }
    }
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.backend.arn
}

resource "aws_apprunner_service" "frontend" {
  service_name = "${var.project_name}-frontend"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = local.ecr_access_role_arn
    }

    image_repository {
      image_identifier      = "${data.aws_ecr_repository.frontend.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "80"
      }
    }
  }

  instance_configuration {
    cpu    = "256"
    memory = "512"
  }

  health_check_configuration {
    protocol            = "HTTP"
    # Standalone frontend on App Runner has no API upstream; index.html on / is enough.
    path                = "/"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  depends_on = [aws_apprunner_service.backend]
}
