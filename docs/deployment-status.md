# Deployment status

This page records **what is actually running today** versus what is **implemented in the
repository**. It exists so reviewers (and teammates) do not have to infer status from the
README diagram alone.

---

## At a glance

| Concern | In code / CI | Live today | Notes |
|---|---|---|---|
| **Public demo (frontend)** | Yes | **Netlify** — https://cloudmlops.netlify.app | Zero-cost reference deployment |
| **Public demo (API)** | Yes | **Render** — https://cloudmlops.onrender.com | Docker Web Service |
| **Database (demo)** | Yes | **Render PostgreSQL** | Internal URL from Render dashboard |
| **AWS App Runner + RDS** | CI job + guide ready | **Not provisioned** | Deploy job skips until `AWS_ACCOUNT_ID` is set |
| **FLAN-T5 abstractive AI** | Yes (`requirements-ai.txt`, `FlanT5Summarizer`) | **No on live demo** | Live `/health` reports `ai_backend: "extractive"` |
| **Extractive fallback** | Yes | **Yes (live demo)** | Active because Render image was built with `INSTALL_AI=false` |
| **GitHub Actions CI** | Yes | Runs on every push | Lint, tests, Postgres integration, Docker build |
| **GitHub Actions deploy** | Yes | **Fails on main if secrets missing** | Requires production env secrets; smoke-tests `flan-t5` |
| **Terraform (App Runner)** | Yes | **Not applied yet** | `infra/terraform/` |

---

## Two deployment paths

### Path A — Reference demo (current, $0)

```
Browser → Netlify (React) → Render (FastAPI + Postgres)
```

- Documented in [`deployment-render-netlify.md`](deployment-render-netlify.md)
- Suitable for sharing a URL with classmates or on a portfolio
- **Does not satisfy** a literal “initial AWS deployment” requirement by itself
- Runs the **extractive** summarizer on the free tier (memory / build-time constraints)

### Path B — Target production (documented, not live)

```
GitHub Actions → ECR → App Runner (backend + frontend) → RDS + S3 + CloudWatch
```

- Documented in [`deployment-aws.md`](deployment-aws.md)
- CI `deploy` job is fully wired (OIDC, ECR push, App Runner rollout, `/health` smoke test)
- **Blocked on account setup**: ECR repos, RDS, IAM roles, App Runner services, GitHub secrets
- When enabled, the deploy build uses `INSTALL_AI=true` and `PREFETCH_MODEL=true` so FLAN-T5
  is baked into the backend image

---

## AI backend: implemented vs live

The proposal calls for **abstractive summarization with FLAN-T5-small**. That is implemented:

| Component | Location |
|---|---|
| Factory pattern (`auto` / `flan-t5` / `extractive`) | `backend/app/ai/factory.py` |
| FLAN-T5 summarizer | `backend/app/ai/flan_t5.py` |
| Extractive fallback | `backend/app/ai/extractive.py` |
| Length strategies | `backend/app/ai/prompts.py` |
| Local Docker default | `INSTALL_AI=true` in `docker-compose.yml` |

**Why the live demo uses extractive:**

1. Render was built with `INSTALL_AI=false` to keep image size and memory within the free
   tier (~512 MB RAM is insufficient for FLAN-T5 + FastAPI + Postgres client overhead).
2. `AI_BACKEND=auto` then resolves to **extractive** when `transformers` / `torch` are absent.
3. `/health` and the dashboard **report the active backend** — there is no silent claim of
   FLAN-T5 when extractive is serving traffic.

**How to demonstrate FLAN-T5 honestly:**

| Audience | What to show |
|---|---|
| Professor / reviewer (local) | `docker compose up --build` → `/health` shows `ai_backend: "flan-t5"` |
| Professor / reviewer (AWS) | Complete Path B; deploy job builds with `PREFETCH_MODEL=true` |
| Live URL only | State clearly: “abstractive model implemented; extractive active on free hosting” |

---

## AWS deploy job — why it does not run yet

From `.github/workflows/ci.yml`:

```yaml
if [ -z "${{ secrets.AWS_ACCOUNT_ID }}" ]; then
  echo "AWS_ACCOUNT_ID is not set; skipping deployment."
```

Required before the job will execute (see [`deployment-aws.md` § Step 9](deployment-aws.md#step-9--turn-on-the-deploy-job)):

| GitHub secret / variable | Purpose |
|---|---|
| `AWS_ACCOUNT_ID` | Enables the deploy job |
| `BACKEND_SERVICE_ARN` | App Runner backend service |
| `FRONTEND_SERVICE_ARN` | App Runner frontend service |
| `BACKEND_PUBLIC_URL` (variable) | Baked into frontend build + smoke test |
| `AWS_REGION` (variable, optional) | Defaults to `us-east-1` |

Plus one-time AWS setup: ECR repositories, RDS instance, VPC connector, IAM
`GitHubActionsDeployRole`, Secrets Manager entries for `DATABASE_URL` and `JWT_SECRET_KEY`.

---

## Proposal alignment checklist

Use this when preparing a submission or demo:

| Requirement | Status | Evidence |
|---|---|---|
| Three-tier architecture (React / FastAPI / PostgreSQL) | Done | Running on Netlify + Render; also `docker compose` |
| Document upload (PDF, DOCX, TXT) | Done | Live demo + tests |
| Abstractive summarization (FLAN-T5) | **Code complete** | `backend/app/ai/`, local Docker, AWS deploy build args |
| Factory / Strategy patterns | Done | `ai/factory.py`, `ai/prompts.py` |
| Auth, history, feedback, admin | Done | Live demo |
| Alembic migrations | Done | Entrypoint + CI Postgres job |
| CI/CD pipeline | Done | `.github/workflows/ci.yml` |
| **Initial AWS deployment** | **Not done** | Guide + job exist; secrets unset |
| Live demo URL | Done | Netlify + Render (documented here) |
| FLAN-T5 on live URL | **No** | Extractive fallback; documented above |

---

## Recommended priority order

1. **Document** — this file + [`deployment-render-netlify.md`](deployment-render-netlify.md) (done in repo).
2. **AWS minimal deploy** — even a single App Runner service + RDS satisfies “initial AWS
   deployment” if your rubric checks for it literally. Follow [`deployment-aws.md`](deployment-aws.md).
3. **Demo strategy for FLAN-T5** — either run `docker compose` during the presentation, or
   complete AWS deploy with `INSTALL_AI=true`, or state in slides that extractive is active
   on the free host by design.

---

## Related documents

| Document | Contents |
|---|---|
| [`deployment-render-netlify.md`](deployment-render-netlify.md) | Live demo setup, env vars, issues log |
| [`deployment-aws.md`](deployment-aws.md) | Target AWS architecture and provisioning steps |
| [`../README.md`](../README.md) | Quick start and configuration |
