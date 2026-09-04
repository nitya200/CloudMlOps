# Team handoff — AWS teammate checklist

One teammate has the AWS account. Everyone else works on the GitHub repo. This page splits
the work so you can finish **initial AWS deployment** without confusion.

**Full commands:** [`deployment-aws.md`](deployment-aws.md)  
**Status / honesty matrix:** [`deployment-status.md`](deployment-status.md)

---

## Roles

| Person | Responsibility |
|---|---|
| **AWS teammate** | Provision ECR, RDS, S3, IAM, App Runner; add GitHub secrets |
| **Repo owner** | Push to `main`, verify CI deploy job runs, share frontend URL for CORS |
| **Everyone** | Do not commit AWS passwords; use Secrets Manager only |

---

## What the AWS teammate does (in order)

### Phase 1 — AWS account setup (~1 hour + RDS wait)

1. Install AWS CLI and run `aws sts get-caller-identity`.
2. Set billing alarm at **$50** (Console → Billing → Budgets).
3. **Step 1** — Create ECR repos: `cloudmlops-backend`, `cloudmlops-frontend`.
4. **Step 2** — Create RDS PostgreSQL 16 (`db.t4g.micro`, private, not public).
5. **Step 3** — Store in Secrets Manager:
   - `cloudmlops/database-url` → `postgresql+psycopg://...`
   - `cloudmlops/jwt-secret` → random 64-char string
   - `cloudmlops/admin-password` → strong admin password
6. **Step 4b** — Create S3 bucket `cloudmlops-uploads-<ACCOUNT_ID>`.
7. **Step 4** — Create IAM roles:
   - `AppRunnerECRAccessRole`
   - `CloudMLOpsInstanceRole` (secrets + logs + S3 prefix)
   - `GitHubActionsDeployRole` (OIDC trust pinned to **your GitHub repo**)

> OIDC trust policy must use your real repo:
> `repo:nitya200/CloudMlOps:ref:refs/heads/main`  
> (adjust owner/name if different)

### Phase 2 — First manual image push (optional but helps debug)

Before CI runs, you can push images once manually (**Step 5** in `deployment-aws.md`):

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1
REG=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Login, build backend WITH AI, push
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REG

docker build --platform linux/amd64 \
  --build-arg INSTALL_AI=true \
  --build-arg PREFETCH_MODEL=true \
  -t $REG/cloudmlops-backend:latest ./backend
docker push $REG/cloudmlops-backend:latest
```

Frontend needs the backend URL — you can use a placeholder first, then rebuild after
backend App Runner exists.

### Phase 3 — App Runner services

8. **Step 6–7** — Create **backend** App Runner service:
   - Image: `cloudmlops-backend:latest`
   - **2 vCPU / 4 GB** (required for FLAN-T5)
   - Port `8000`, health check `/health`
   - VPC connector to RDS
   - Wire Secrets Manager for DB + JWT
   - Env: `ENVIRONMENT=production`, `AI_BACKEND=auto`, `STORAGE_BACKEND=s3`,
     `S3_BUCKET=cloudmlops-uploads-<ACCOUNT_ID>`, `RUN_MIGRATIONS=true`

9. **Step 8** — Create **frontend** App Runner service:
   - Image: `cloudmlops-frontend:latest`
   - 0.25 vCPU / 0.5 GB, port `80`
   - Build with `VITE_API_BASE_URL=https://<backend-apprunner-url>`

10. Copy both **App Runner service ARNs** and the **backend public URL**.

### Phase 4 — GitHub secrets (repo Settings → Environments → `production`)

| Kind | Name | Who sets it | Value |
|---|---|---|---|
| Secret | `AWS_ACCOUNT_ID` | AWS teammate | 12-digit account ID |
| Secret | `BACKEND_SERVICE_ARN` | AWS teammate | Backend App Runner ARN |
| Secret | `FRONTEND_SERVICE_ARN` | AWS teammate | Frontend App Runner ARN |
| Variable | `BACKEND_PUBLIC_URL` | AWS teammate | `https://xxxxx.awsapprunner.com` |
| Variable | `AWS_REGION` | AWS teammate | e.g. `us-east-1` |

**Do not** put database passwords or JWT keys in GitHub — only ARNs and public URLs.

### Phase 5 — Trigger CI deploy

11. Repo owner pushes to `main` (or AWS teammate if they have write access).
12. Open GitHub Actions → **Deploy to AWS** job.
13. Confirm it does **not** say “AWS_ACCOUNT_ID is not set; skipping”.
14. Wait for smoke test: `/health` must return `"status":"ok"`.

### Phase 6 — CORS + verify FLAN-T5

15. AWS teammate updates backend App Runner env:
    ```
    CORS_ORIGINS=https://<frontend-apprunner-url>
    ```
16. Verify:
    ```bash
    curl https://<backend-url>/health
    ```
    Expect: `"database":"connected"` and `"ai_backend":"flan-t5"` (not `extractive`).

---

## What to send back to the team (safe to share in chat)

| Item | Example | Secret? |
|---|---|---|
| Backend URL | `https://abc123.us-east-1.awsapprunner.com` | No — public |
| Frontend URL | `https://def456.us-east-1.awsapprunner.com` | No — public |
| Admin login | `admin@cloudmlops.app` + password from Secrets Manager | Password — share privately |
| `/health` screenshot | Shows `flan-t5` + `connected` | No |
| AWS_ACCOUNT_ID | 12 digits | Low risk — still use GitHub secret only |

**Never share in WhatsApp/Discord:** RDS password, JWT secret, Secrets Manager values.

---

## Cost control (student project)

| Action | Why |
|---|---|
| Set **$50 billing alarm** | Avoid surprise charges |
| **Pause** App Runner when not demoing | Stops compute billing |
| Keep RDS `db.t4g.micro` single-AZ | Cheapest Postgres option |
| Delete old ECR images | Lifecycle policy in deployment guide |

---

## If something fails

| Symptom | Check |
|---|---|
| Deploy job skipped | `AWS_ACCOUNT_ID` secret missing in `production` environment |
| OIDC assume role failed | Trust policy repo name wrong; OIDC provider not created in IAM |
| Health `degraded` | RDS security group / VPC connector; `DATABASE_URL` secret wrong |
| `ai_backend: extractive` | Image built with `INSTALL_AI=false`; rebuild with `true` |
| CORS on login | `CORS_ORIGINS` must match frontend URL exactly |
| Deploy job green but site 502 | App Runner still rolling out; wait or check service logs |

---

## Relationship to Netlify + Render demo

The **live class demo** may stay on Netlify + Render (`deployment-render-netlify.md`).
AWS is the **target production path** for the proposal’s “initial AWS deployment” requirement.
Both can coexist — document which URL you show in the presentation.

| URL | AI backend | Satisfies AWS requirement? |
|---|---|---|
| cloudmlops.netlify.app + Render | extractive | No |
| App Runner URLs | flan-t5 (if 2 vCPU / 4 GB) | Yes |

---

## Quick message to forward to your AWS teammate

Copy-paste:

```
Hi — can you provision AWS for CloudMLOps? Follow docs/team-aws-handoff.md in the repo
(full commands in docs/deployment-aws.md).

Need from you:
1. ECR + RDS + S3 + IAM (GitHubActionsDeployRole with OIDC for our repo)
2. Two App Runner services (backend 2vCPU/4GB, frontend small)
3. GitHub production secrets: AWS_ACCOUNT_ID, BACKEND_SERVICE_ARN, FRONTEND_SERVICE_ARN
4. GitHub variable: BACKEND_PUBLIC_URL
5. Send back both public URLs when done

Repo: https://github.com/nitya200/CloudMlOps
After secrets are set, we'll push to main and CI should deploy automatically.
```
