# Deployment status

This page records **what is actually running today** versus what is **implemented in the
repository**.

---

## At a glance

| Concern | In code / CI | Live today | Notes |
|---|---|---|---|
| **AWS production (frontend)** | Yes | **https://asqmhsdwfs.us-east-2.awsapprunner.com** | App Runner + ECR — primary live UI |
| **AWS production (API)** | Yes | **https://p3jivcdmbf.us-east-2.awsapprunner.com** | RDS PostgreSQL, S3 uploads |
| **Reference demo (frontend)** | Yes | https://cloudmlops.netlify.app | Zero-cost Netlify |
| **Reference demo (API)** | Yes | https://cloudmlops.onrender.com | Render free tier |
| **AI on AWS** | Yes | **FLAN-T5** (`AI_BACKEND=flan-t5`, 2 vCPU / 4 GB) | Verify via `/health` |
| **FLAN-T5 abstractive AI** | Yes | Local Docker + optional AWS GPU path | `backend/app/ai/flan_t5.py` |
| **Model registry / retraining (UC-12, UC-16)** | Yes | API + admin UI | ROUGE evaluation, approve, promote |
| **GitHub Actions CI** | Yes | Every push/PR | Lint, tests, Postgres integration, Docker |
| **GitHub Actions deploy** | Yes | On push to `main` when secrets set | ECR + App Runner rollout |
| **Terraform (App Runner)** | Yes | Applied in `us-east-2` | `infra/terraform/` |

---

## Two deployment paths

### Path A — Reference demo ($0)

```
Browser → Netlify (React) → Render (FastAPI + Postgres)
```

Documented in [`deployment-render-netlify.md`](deployment-render-netlify.md). Uses the
extractive summarizer on the free tier.

### Path B — AWS production (live)

```
GitHub Actions → ECR → App Runner (backend + frontend) → RDS + S3 + CloudWatch
```

Documented in [`deployment-aws.md`](deployment-aws.md). Production summarization uses
**extractive** for reliable sub-120s responses; the backend image still includes FLAN-T5 for
local demos and future GPU instances.

---

## Proposal alignment checklist

| Requirement | Status | Evidence |
|---|---|---|
| Three-tier architecture (React / FastAPI / PostgreSQL) | Done | AWS URLs above + `docker compose` |
| Document upload (PDF, DOCX, TXT) | Done | Live + tests |
| Abstractive summarization (FLAN-T5) | Code complete | Local Docker; AWS uses extractive by policy |
| Factory / Strategy patterns | Done | `ai/factory.py`, `ai/prompts.py` |
| Auth, history, feedback, admin | Done | Live demo |
| **UC-12: Admin approve/promote model version** | Done | `/api/admin/model-versions/*`, Admin dashboard |
| **UC-16: Trigger retraining / register version** | Done | `POST /api/admin/training-jobs`, ROUGE evaluation |
| Alembic migrations | Done | `0002_model_lifecycle` + CI Postgres job |
| CI/CD pipeline | Done | `.github/workflows/ci.yml` |
| **Initial AWS deployment** | Done | App Runner services verified via `/health` |
| Live demo URL | Done | AWS + Netlify/Render |

---

## Related documents

| Document | Contents |
|---|---|
| [`deployment-render-netlify.md`](deployment-render-netlify.md) | Netlify + Render setup |
| [`deployment-aws.md`](deployment-aws.md) | AWS architecture and provisioning |
| [`../README.md`](../README.md) | Quick start and configuration |
