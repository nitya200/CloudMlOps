output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "backend_service_url" {
  description = "Set GitHub variable BACKEND_PUBLIC_URL to this value (no trailing slash)."
  value       = "https://${aws_apprunner_service.backend.service_url}"
}

output "frontend_service_url" {
  value = "https://${aws_apprunner_service.frontend.service_url}"
}

output "backend_service_arn" {
  description = "GitHub secret BACKEND_SERVICE_ARN"
  value       = aws_apprunner_service.backend.arn
}

output "frontend_service_arn" {
  description = "GitHub secret FRONTEND_SERVICE_ARN"
  value       = aws_apprunner_service.frontend.arn
}

output "vpc_connector_arn" {
  value = var.enable_vpc_connector ? aws_apprunner_vpc_connector.main[0].arn : null
}

output "github_actions_role_arn" {
  description = "OIDC role assumed by the deploy job (name: GitHubActionsDeployRole)."
  value       = local.github_deploy_arn
}

output "github_secrets_checklist" {
  value = <<-EOT
    GitHub → Settings → Environments → production:
      Secret  AWS_ACCOUNT_ID         = ${data.aws_caller_identity.current.account_id}
      Secret  BACKEND_SERVICE_ARN    = ${aws_apprunner_service.backend.arn}
      Secret  FRONTEND_SERVICE_ARN   = ${aws_apprunner_service.frontend.arn}
      Variable AWS_REGION            = ${var.aws_region}
      Variable BACKEND_PUBLIC_URL    = https://${aws_apprunner_service.backend.service_url}
    After frontend URL is known, update backend CORS_ORIGINS to:
      https://${aws_apprunner_service.frontend.service_url}
  EOT
}
