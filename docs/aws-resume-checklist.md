# AWS resume checklist (account 569486438576, us-east-2)

Use this after a break. You completed **Steps 0–5**. Continue from **Step 6**.

## One-time on your PC (required before scripts work)

1. **Install AWS CLI** — https://aws.amazon.com/cli/  
   (If winget prompts, click **Yes** on the admin/UAC dialog.)

2. **Configure credentials** (never paste keys in chat):
   ```powershell
   aws configure
   ```
   - Region: `us-east-2`
   - Output: `json`

3. **Test**:
   ```powershell
   aws sts get-caller-identity
   ```

4. **Start Docker Desktop**

## Automated steps (after AWS CLI works)

From repo root:

```powershell
cd D:\CloudMLOps

# Check everything still exists
.\scripts\aws-resume-deploy.ps1 -Action verify

# Step 6 — VPC connector + App Runner (pick one)
# Option A — Terraform (recommended): cd infra\terraform && terraform apply
# Option B — script (connector only): .\scripts\aws-resume-deploy.ps1 -Action vpc-connector

# Step 7 — Build and push backend image (~15-20 min)
.\scripts\aws-resume-deploy.ps1 -Action push-backend
```

## Step 8 — App Runner backend (Console)

App Runner → Create service → ECR `cloudmlops-backend:latest`

| Setting | Value |
|---|---|
| ECR access role | `AppRunnerECRAccessRole` |
| Port | `8000` |
| Health check | `/health` |
| CPU / Memory | **2 vCPU / 4 GB** |
| Instance role | `CloudMLOpsInstanceRole` |
| VPC connector | `cloudmlops-connector` |

**Environment variables:** `ENVIRONMENT=production`, `LOG_JSON=true`, `AUTO_CREATE_SCHEMA=false`, `RUN_MIGRATIONS=true`, `AI_BACKEND=flan-t5`, `AI_EAGER_LOAD=true`, `STORAGE_BACKEND=s3`, `S3_BUCKET=cloudmlops-uploads-569486438576`, `S3_PREFIX=documents`, `S3_REGION=us-east-2`, `SEED_ADMIN=true`, `ADMIN_EMAIL=admin@cloudmlops.app`, `CORS_ORIGINS=https://placeholder`

**Secrets (link from Secrets Manager):** `DATABASE_URL` → `cloudmlops/database-url`, `JWT_SECRET_KEY` → `cloudmlops/jwt-secret`, `ADMIN_PASSWORD` → `cloudmlops/admin-password`

Test: `https://YOUR-BACKEND/health` → `"database":"connected"`, `"ai_backend":"flan-t5"`

## Step 9 — Frontend

```powershell
.\scripts\aws-resume-deploy.ps1 -Action push-frontend -BackendUrl https://YOUR-BACKEND-URL
```

App Runner → Create service → `cloudmlops-frontend:latest`, port **80**, 0.25 vCPU / 0.5 GB, no VPC.

Update backend `CORS_ORIGINS` to frontend URL → redeploy backend.

## Step 10 — GitHub (optional CI deploy)

```powershell
.\scripts\aws-resume-deploy.ps1 -Action print-github-secrets
```

Add to GitHub → Settings → Environments → `production`: secrets `AWS_ACCOUNT_ID`, `BACKEND_SERVICE_ARN`, `FRONTEND_SERVICE_ARN`; variables `BACKEND_PUBLIC_URL`, `AWS_REGION=us-east-2`.

## Login after deploy

| Field | Value |
|---|---|
| Email | `admin@cloudmlops.app` |
| Password | Value in `cloudmlops/admin-password` secret (e.g. `MyCloudAdmin2026!`) |

## Already completed (do not redo)

- ECR: `cloudmlops-backend`, `cloudmlops-frontend`
- RDS: `database-1` (Aurora PostgreSQL)
- S3: `cloudmlops-uploads-569486438576`
- Secrets: `cloudmlops/database-url`, `jwt-secret`, `admin-password`
- IAM: `AppRunnerECRAccessRole`, `CloudMLOpsInstanceRole`, `GitHubActionsDeployRole`
