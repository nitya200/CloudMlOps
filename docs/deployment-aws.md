# AWS deployment guide

**Status: the application is deployment-ready; the AWS account is not provisioned yet.**

What is already implemented in the repository:

- Alembic migrations, applied automatically by the container entrypoint before uvicorn
  starts, with retries while RDS finishes booting.
- An S3 storage backend (`STORAGE_BACKEND=s3`) so uploads survive redeploys and scale-out.
- A startup guard that refuses to run in production with insecure defaults.
- Rate limiting on the credential endpoints.
- A `deploy` job in `.github/workflows/ci.yml` that authenticates with OIDC, pushes both
  images to ECR, rolls out App Runner and smoke-tests `/health`.

What remains is account setup: creating the ECR repositories, RDS instance, IAM roles,
VPC connector and App Runner services described below, then setting the GitHub secrets
listed in [step 9](#step-9--turn-on-the-deploy-job). The deploy job skips itself until
`AWS_ACCOUNT_ID` exists, so nothing breaks in the meantime.

Deliberately out of scope, matching the simplified proposal: Terraform, automated retraining,
model promotion workflows, DistilBART comparison and blue/green deployment.

---

## Target architecture

```
                        GitHub (main branch)
                                │
                                ▼
                         GitHub Actions
                    lint → test → build → push
                                │
                                ▼
                      Amazon ECR (2 repos)
                   cloudmlops-backend / -frontend
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
      App Runner: backend              App Runner: frontend
      FastAPI + FLAN-T5                Nginx + React bundle
      2 vCPU / 4 GB                    0.25 vCPU / 0.5 GB
                 │                             │
                 │  VPC connector              │  HTTPS (public)
                 ▼                             ▼
      Amazon RDS PostgreSQL 16            End users
      db.t4g.micro, private subnet
                 │
                 ▼
      CloudWatch Logs / Metrics / Alarms
```

Why App Runner rather than ECS or EKS: it terminates TLS, gives each service an HTTPS
hostname, autoscales on concurrency and deploys straight from an ECR tag, with no load
balancer, task definition or cluster to manage. The trade-off is less control over
networking and no GPU — which is exactly why the project uses FLAN-T5-**small** on CPU.

---

## Sizing and cost

FLAN-T5-small needs roughly 300 MB for weights plus headroom for activations; 4 GB is
comfortable and leaves room for concurrent requests.

| Resource | Configuration | Approximate monthly cost (us-east-1) |
|---|---|---|
| App Runner — backend | 2 vCPU / 4 GB, min 1 instance | $50–70 |
| App Runner — frontend | 0.25 vCPU / 0.5 GB | $5–10 |
| RDS PostgreSQL | db.t4g.micro, 20 GB gp3, single-AZ | $15–20 |
| ECR storage | ~2 GB of images | < $1 |
| CloudWatch | logs, metrics, 3 alarms | $2–5 |
| Data transfer | light demo traffic | $1–3 |
| **Total** | | **≈ $75–110 / month** |

Cost controls for a student project: set App Runner minimum size to 1 instance and **pause
the service** when you are not demonstrating it (pausing stops compute billing while keeping
the configuration), keep RDS single-AZ, and set a billing alarm at $50 before you begin.

---

## Prerequisites

```bash
aws --version                 # AWS CLI v2
aws configure                 # or aws sso login
aws sts get-caller-identity   # confirm the account

export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1
```

---

## Step 1 — Create the ECR repositories

```bash
for repo in cloudmlops-backend cloudmlops-frontend; do
  aws ecr create-repository \
    --repository-name $repo \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability MUTABLE \
    --region $AWS_REGION
done
```

Add a lifecycle policy so old images do not accumulate charges:

```bash
cat > lifecycle.json <<'EOF'
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep only the 10 most recent images",
    "selection": { "tagStatus": "any", "countType": "imageCountMoreThanNumber", "countNumber": 10 },
    "action": { "type": "expire" }
  }]
}
EOF

aws ecr put-lifecycle-policy --repository-name cloudmlops-backend \
  --lifecycle-policy-text file://lifecycle.json
```

---

## Step 2 — Provision RDS PostgreSQL

```bash
# Security group that only App Runner's VPC connector may enter
aws ec2 create-security-group \
  --group-name cloudmlops-rds-sg \
  --description "CloudMLOps RDS access" \
  --vpc-id vpc-xxxxxxxx

aws rds create-db-instance \
  --db-instance-identifier cloudmlops-db \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version 16.4 \
  --master-username cloudmlops \
  --master-user-password "$(openssl rand -base64 24)" \
  --allocated-storage 20 \
  --storage-type gp3 \
  --db-name cloudmlops \
  --backup-retention-period 7 \
  --no-publicly-accessible \
  --vpc-security-group-ids sg-xxxxxxxx \
  --region $AWS_REGION
```

Keep `--no-publicly-accessible`. The database is reached only through the App Runner VPC
connector, so it is never exposed to the internet.

**Schema.** Nothing to do by hand. The container entrypoint runs `alembic upgrade head`
before uvicorn starts, retrying while RDS accepts connections, so the first deployment
creates the schema and every later deployment applies pending migrations.

Do **not** apply `database/schema.sql` to this database. It is reference documentation;
letting both it and Alembic create tables gives two sources of truth, which is exactly how
the ORM enum values and the DDL CHECK constraints drifted apart once before.

Keep `AUTO_CREATE_SCHEMA=false` in production (the image already defaults to this).
`create_all` adds missing tables but never alters existing ones, so the second schema
change would silently fail to apply.

---

## Step 3 — Store secrets in Secrets Manager

Never put the database password or JWT key in App Runner's plaintext environment variables.

```bash
aws secretsmanager create-secret \
  --name cloudmlops/database-url \
  --secret-string "postgresql+psycopg://cloudmlops:<password>@<rds-endpoint>:5432/cloudmlops"

aws secretsmanager create-secret \
  --name cloudmlops/jwt-secret \
  --secret-string "$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"

aws secretsmanager create-secret \
  --name cloudmlops/admin-password \
  --secret-string 'ChooseAStrongAdminPassword123!'
```

App Runner references these by ARN, and the value never appears in the console, the image or
the repository.

---

## Step 4 — IAM roles

Two distinct roles, following least privilege.

**Access role** — lets App Runner pull from ECR:

```bash
aws iam create-role --role-name AppRunnerECRAccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "build.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

**Instance role** — what the running container itself may do: read its secrets, write its
logs, and read/write only its own prefix in the uploads bucket.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:cloudmlops/*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:<account-id>:log-group:/aws/apprunner/cloudmlops-*:*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::cloudmlops-uploads-<account-id>/documents/*"
    }
  ]
}
```

Object-level actions only, scoped to the `documents/` prefix: the container never needs to
list or delete the bucket itself.

**GitHub deploy role** — assumed by the `deploy` job over OIDC, so no long-lived AWS keys
are ever stored in GitHub. The trust policy must pin the repository, otherwise any GitHub
repository could assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:ref:refs/heads/main"
      }
    }
  }]
}
```

Name it `GitHubActionsDeployRole` — that is the name the workflow assumes. It needs ECR
push permissions (`AmazonEC2ContainerRegistryPowerUser`) plus `apprunner:StartDeployment`
and `apprunner:DescribeService` on the two services.

---

## Step 4b — Create the uploads bucket

App Runner's instance storage is ephemeral and per instance: a redeploy wipes it, and with
two instances behind one URL the instance serving a download is often not the one that took
the upload. Extracted text lives in RDS, so summaries and history are unaffected either
way, but the original files need somewhere durable.

```bash
aws s3api create-bucket --bucket cloudmlops-uploads-$AWS_ACCOUNT_ID --region $AWS_REGION

aws s3api put-public-access-block --bucket cloudmlops-uploads-$AWS_ACCOUNT_ID \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-bucket-encryption --bucket cloudmlops-uploads-$AWS_ACCOUNT_ID \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

Uploads are private user documents, so blocking public access is not optional.

---

## Step 5 — Push the images

```bash
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

REG=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Backend. PREFETCH_MODEL bakes the FLAN-T5 weights into the image so the
# container does not download 300 MB from Hugging Face on every cold start.
docker build --platform linux/amd64 \
  --build-arg INSTALL_AI=true \
  --build-arg PREFETCH_MODEL=true \
  -t $REG/cloudmlops-backend:latest ./backend
docker push $REG/cloudmlops-backend:latest

# Frontend. The API URL is compiled into the bundle at build time, so the
# backend service must exist first (or be redeployed after).
docker build --platform linux/amd64 \
  --build-arg VITE_API_BASE_URL=https://<backend-id>.us-east-1.awsapprunner.com \
  -t $REG/cloudmlops-frontend:latest ./frontend
docker push $REG/cloudmlops-frontend:latest
```

`--platform linux/amd64` matters if you build on an Apple Silicon machine; App Runner runs
x86_64 and will fail with an exec format error otherwise.

---

## Step 6 — Create the VPC connector

```bash
aws apprunner create-vpc-connector \
  --vpc-connector-name cloudmlops-connector \
  --subnets subnet-aaaa subnet-bbbb \
  --security-groups sg-xxxxxxxx
```

Use private subnets in at least two availability zones. This connector is what lets the
backend reach a non-public RDS instance.

---

## Step 7 — Deploy the backend service

```json
{
  "ServiceName": "cloudmlops-backend",
  "SourceConfiguration": {
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::<account-id>:role/AppRunnerECRAccessRole"
    },
    "AutoDeploymentsEnabled": true,
    "ImageRepository": {
      "ImageIdentifier": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudmlops-backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "ENVIRONMENT": "production",
          "LOG_JSON": "true",
          "LOG_LEVEL": "INFO",
          "AUTO_CREATE_SCHEMA": "false",
          "RUN_MIGRATIONS": "true",
          "AI_BACKEND": "flan-t5",
          "AI_MODEL_NAME": "google/flan-t5-small",
          "AI_EAGER_LOAD": "true",
          "MAX_UPLOAD_SIZE_MB": "10",
          "STORAGE_BACKEND": "s3",
          "S3_BUCKET": "cloudmlops-uploads-<account-id>",
          "S3_PREFIX": "documents",
          "S3_REGION": "us-east-1",
          "SEED_ADMIN": "true",
          "ADMIN_EMAIL": "admin@cloudmlops.app",
          "CORS_ORIGINS": "https://<frontend-id>.us-east-1.awsapprunner.com"
        },
        "RuntimeEnvironmentSecrets": {
          "DATABASE_URL": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:cloudmlops/database-url",
          "JWT_SECRET_KEY": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:cloudmlops/jwt-secret",
          "ADMIN_PASSWORD": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:cloudmlops/admin-password"
        }
      }
    }
  },
  "InstanceConfiguration": {
    "Cpu": "2 vCPU",
    "Memory": "4 GB",
    "InstanceRoleArn": "arn:aws:iam::<account-id>:role/CloudMLOpsInstanceRole"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 20,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  },
  "NetworkConfiguration": {
    "EgressConfiguration": {
      "EgressType": "VPC",
      "VpcConnectorArn": "arn:aws:apprunner:us-east-1:<account-id>:vpcconnector/cloudmlops-connector/1/..."
    }
  }
}
```

```bash
aws apprunner create-service --cli-input-json file://backend-service.json
```

Two settings deserve attention. `AI_EAGER_LOAD=true` loads the model during the lifespan
startup hook so the first user request is not the one that pays the several-second load cost.
And the health check `Path` is `/health` — the endpoint returns HTTP 200 with
`status: "degraded"` when the database is unreachable, so a transient RDS blip surfaces as a
readable diagnostic rather than a crash-looping container.

**Autoscaling.** Summarization is CPU-bound and each container holds a model in memory, so
keep concurrency low and scale out with instances:

```bash
aws apprunner create-auto-scaling-configuration \
  --auto-scaling-configuration-name cloudmlops-scaling \
  --max-concurrency 4 --min-size 1 --max-size 4
```

---

## Step 8 — Deploy the frontend service

Same shape, much smaller, and no VPC connector or secrets — it is a static bundle behind
Nginx.

| Setting | Value |
|---|---|
| Image | `cloudmlops-frontend:latest` |
| Port | `80` |
| CPU / memory | 0.25 vCPU / 0.5 GB |
| Health check path | `/health` |
| Egress | default (public) |

After it comes up, take its URL and set it as `CORS_ORIGINS` on the backend, then redeploy
the backend so browser requests are accepted.

---

## Step 9 — Turn on the deploy job

The `deploy` job already exists in `.github/workflows/ci.yml`. It runs only on a push to
`main`, only after `backend`, `backend-integration`, `frontend` and `docker` all pass, and
**skips itself entirely while `AWS_ACCOUNT_ID` is unset** — so it is inert until you
complete this step, and stays inert on forks.

To activate it, add these to the repository's `production` environment:

| Kind | Name | Value |
|---|---|---|
| Secret | `AWS_ACCOUNT_ID` | 12-digit account id |
| Secret | `BACKEND_SERVICE_ARN` | App Runner ARN from step 7 |
| Secret | `FRONTEND_SERVICE_ARN` | App Runner ARN from step 8 |
| Variable | `AWS_REGION` | e.g. `us-east-1` (defaults to `us-east-1`) |
| Variable | `BACKEND_PUBLIC_URL` | `https://<backend-id>.us-east-1.awsapprunner.com` |

Set `BACKEND_PUBLIC_URL` before the first deploy: it is compiled into the frontend bundle
at build time and is also the URL the smoke test probes.

What the job does, and why each part earns its place:

- **OIDC, not access keys.** `permissions: id-token: write` lets the runner exchange a
  short-lived GitHub token for AWS credentials, so there is no long-lived secret to leak.
- **Explicit `start-deployment` and polling.** `AutoDeploymentsEnabled: true` makes App
  Runner redeploy on its own when a new `:latest` lands, but that happens asynchronously —
  the pipeline would report green while the rollout was still failing. Polling until
  `RUNNING` is what makes a bad deploy actually fail the build.
- **A health check that reads the body.** A 200 is not enough. `/health` returns
  `status: "degraded"` when the service is up but cannot reach RDS, which is precisely the
  failure worth catching, so the job greps for `"status":"ok"`.

Three IAM identities are involved and it is worth keeping them straight:
`GitHubActionsDeployRole` is assumed by the pipeline (push to ECR, call App Runner),
`AppRunnerECRAccessRole` is assumed by App Runner to pull the image, and
`CloudMLOpsInstanceRole` is assumed by the running container (read secrets, write logs,
read/write its S3 prefix). None can do another's job.

### Migrations during a deploy

The container entrypoint runs `alembic upgrade head` before uvicorn binds a port, so App
Runner's health check cannot pass until the schema is current. With more than one instance,
several will race to migrate; Alembic takes a lock on `alembic_version`, so the losers wait
and then find nothing to do. Two rules keep that safe:

- Write migrations that are backwards compatible with the *previous* image, because both
  versions run simultaneously during a rollout. Add a nullable column first, backfill it,
  and only make it `NOT NULL` in a later deploy.
- For a long-running migration, set `RUN_MIGRATIONS=false` on the service and run
  `alembic upgrade head` once from a bastion host instead, so instance startup does not
  time out.

---

## Step 10 — CloudWatch monitoring

Because the backend sets `LOG_JSON=true`, every log line arrives as structured JSON with
`request_id`, `level`, `logger` and message fields, which makes Logs Insights queries useful
rather than a text search.

**Log groups**

```
/aws/apprunner/cloudmlops-backend/<service-id>/application
/aws/apprunner/cloudmlops-backend/<service-id>/service
/aws/apprunner/cloudmlops-frontend/<service-id>/application
```

**Useful queries**

```sql
-- Slowest summarization requests
fields @timestamp, request_id, processing_time_seconds, summary_length
| filter ispresent(processing_time_seconds)
| sort processing_time_seconds desc
| limit 20

-- Errors grouped by domain error code
fields @timestamp, code, error_message
| filter level = "ERROR"
| stats count() by code
| sort count desc

-- Trace one request end to end
fields @timestamp, logger, message
| filter request_id = "a3f9c1e08b2d4a71"
| sort @timestamp asc
```

**Alarms worth having**

| Alarm | Condition | Why |
|---|---|---|
| Backend 5xx | `5xxStatusResponses` > 5 in 5 min | Something is broken for users |
| High latency | p95 `RequestLatency` > 15 s | Model is saturated; scale out |
| CPU saturation | `CPUUtilization` > 85 % for 10 min | Instance is undersized |
| RDS storage | `FreeStorageSpace` < 2 GB | Database is filling up |
| RDS connections | `DatabaseConnections` > 40 | Connection pool leak |
| Billing | estimated charges > $50 | Cost guard rail |

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name cloudmlops-backend-5xx \
  --namespace AWS/AppRunner \
  --metric-name 5xxStatusResponses \
  --dimensions Name=ServiceName,Value=cloudmlops-backend \
  --statistic Sum --period 300 --evaluation-periods 1 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:<account-id>:cloudmlops-alerts
```

A dashboard combining request count, p95 latency, CPU/memory, RDS connections and the error
count gives you one screen to show during a demo.

---

## Verifying a deployment

```bash
BASE=https://<backend-id>.us-east-1.awsapprunner.com

# 1. Health, including which AI backend actually loaded
curl -s $BASE/health | jq

# 2. OpenAPI docs render
curl -sI $BASE/docs | head -1

# 3. Full round trip
TOKEN=$(curl -sX POST $BASE/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@cloudmlops.app","password":"<admin-password>"}' | jq -r .access_token)

curl -sX POST $BASE/api/summaries/text -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"<at least 200 characters of text>","summary_length":"short"}' | jq
```

If `/health` reports `"model_loaded": false` while `"ai_backend": "flan-t5"`, the container
could not load the weights — check that the image was built with `INSTALL_AI=true` and that
memory is at least 4 GB.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Service stuck in `OPERATION_IN_PROGRESS` | Health check failing | Read the application log group; usually the database is unreachable |
| `exec format error` | Image built for arm64 | Rebuild with `--platform linux/amd64` |
| Health check passes, `status: "degraded"` and `database: "unavailable"` | RDS security group or connector | Allow the connector's security group on port 5432 |
| Container killed during summarization | Out of memory | Raise to 4 GB, or set `AI_BACKEND=extractive` |
| First request after deploy takes 20 s | Model downloading at runtime | Rebuild with `PREFETCH_MODEL=true` |
| Browser shows CORS errors | `CORS_ORIGINS` missing the frontend URL | Update the variable and redeploy the backend |
| Uploads fail at ~1 MB | Nginx body limit | `client_max_body_size` in `frontend/nginx.conf` |
| Logins stop working after redeploy | `JWT_SECRET_KEY` changed | Always source it from Secrets Manager, never regenerate |
| Container exits immediately, log says "Refusing to start" | Production guard tripped | Set a real `JWT_SECRET_KEY` / `ADMIN_PASSWORD`; do not use the defaults |
| Startup loops on "Migration attempt N failed" | RDS unreachable from the connector | Check the security group; after 10 attempts the container exits by design |
| `relation "users" already exists` on first deploy | `database/schema.sql` was applied by hand | Alembic owns the schema; `alembic stamp head` on the existing database |
| Uploaded file 404s on download | Two instances, `STORAGE_BACKEND=local` | Set `STORAGE_BACKEND=s3` with `S3_BUCKET` |
| `429 rate_limited` during a demo | Login throttle, per IP | Expected; wait for `Retry-After`, or raise `LOGIN_RATE_LIMIT` |

---

## Teardown

App Runner bills for provisioned compute whether or not anyone is using it, so remember this
section.

```bash
# Pause instead of delete when you still need the service for a later demo
aws apprunner pause-service --service-arn <arn>

# Full teardown
aws apprunner delete-service --service-arn <backend-arn>
aws apprunner delete-service --service-arn <frontend-arn>
aws apprunner delete-vpc-connector --vpc-connector-arn <arn>
aws rds delete-db-instance --db-instance-identifier cloudmlops-db \
  --final-db-snapshot-identifier cloudmlops-final
aws ecr delete-repository --repository-name cloudmlops-backend --force
aws ecr delete-repository --repository-name cloudmlops-frontend --force
```

---

## How the local and cloud environments map to each other

The same image runs in both; only environment variables differ. That is the point of keeping
all configuration in `app/core/config.py`.

| Concern | Local | AWS |
|---|---|---|
| Frontend | Vite dev server / Nginx container | App Runner (0.25 vCPU) |
| Backend | Uvicorn container | App Runner (2 vCPU / 4 GB) |
| Database | `postgres:16-alpine` container | RDS PostgreSQL 16, private subnet |
| Schema | `alembic upgrade head` in the entrypoint | identical — same entrypoint |
| Uploads | `STORAGE_BACKEND=local`, Docker volume | `STORAGE_BACKEND=s3`, private bucket |
| Secrets | `.env` file | Secrets Manager ARNs |
| Logs | `docker compose logs` | CloudWatch Logs (JSON) |
| Images | Local Docker daemon | Amazon ECR |
| TLS | none | Terminated by App Runner |

The only meaningful difference is where uploaded bytes land, and it is a configuration
change rather than a code change: `DocumentService` talks to a `StorageBackend` interface
with `local` and `s3` implementations behind it.

### Remaining limitation

Rate-limit counters are held in each process, so *N* instances allow *N* times the
configured budget. Moving them to ElastiCache would make the limit exact; the per-instance
limit is still enough to turn an unbounded online password attack into a slow one, and
`app/core/rate_limit.py` is the single seam where a shared backend would slot in.
