# CloudMLOps AWS infrastructure (Terraform)

Minimum Terraform to wire **existing** ECR, RDS, S3, and Secrets Manager resources into
**App Runner** services with a **VPC connector** for private database access.

Does **not** recreate the application — it deploys the existing Docker images from ECR.

## What Terraform creates

| Resource | Purpose |
|---|---|
| `aws_apprunner_vpc_connector` | Backend → RDS over private network |
| `aws_security_group_rule` | Allow connector SG → RDS on 5432 |
| `aws_apprunner_service` (backend) | FastAPI + FLAN-T5, 2 vCPU / 4 GB, `AI_BACKEND=flan-t5` |
| `aws_apprunner_service` (frontend) | Nginx + React from ECR |

Optional (when `create_iam_roles = true`): OIDC provider + three IAM roles.

## Prerequisites (already done in your account)

- ECR: `cloudmlops-backend`, `cloudmlops-frontend` (**with `:latest` images pushed**)
- RDS: cluster `database-1` (Aurora PostgreSQL)
- S3: `cloudmlops-uploads-<account-id>`
- Secrets Manager: `cloudmlops/database-url`, `jwt-secret`, `admin-password`
- IAM: `AppRunnerECRAccessRole`, `CloudMLOpsInstanceRole`, `GitHubActionsDeployRole`

## Bootstrap order

```bash
# 1. Push images (from repo root, AWS CLI configured)
./scripts/aws-resume-deploy.ps1 -Action push-backend   # ~15–20 min
# After terraform apply gives backend URL:
./scripts/aws-resume-deploy.ps1 -Action push-frontend -BackendUrl https://....awsapprunner.com

# 2. Terraform
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit github_repository, s3_bucket_name
terraform init
terraform plan
terraform apply

# 3. GitHub production environment (from terraform output)
#    AWS_ACCOUNT_ID, BACKEND_SERVICE_ARN, FRONTEND_SERVICE_ARN, BACKEND_PUBLIC_URL, AWS_REGION

# 4. Push to main → CI deploy job builds, pushes, rolls out, smoke-tests /health
```

Or use **Actions → AWS Infrastructure → Run workflow → apply** (requires `AWS_S3_BUCKET` variable).

### Extra IAM for Terraform via GitHub Actions

If `GitHubActionsDeployRole` was created only for ECR/App Runner deploy, attach a policy
allowing Terraform to manage VPC connectors, security group rules, VPC endpoints, and
App Runner services (or run `terraform apply` locally with an admin profile instead).

## GitHub variables for aws-infra workflow

| Variable | Example |
|---|---|
| `AWS_REGION` | `us-east-2` |
| `AWS_S3_BUCKET` | `cloudmlops-uploads-569486438576` |
| `AWS_DB_CLUSTER_ID` | `database-1` |
| `CORS_ORIGINS` | `https://cloudmlops.netlify.app` |
