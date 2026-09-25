# Proposal checklist v2 — implementation status

This updates `CloudMLOps_Proposal_Checklist_v2.docx` (Sept 21, 2026) against the **current repository**.

Legend: **Done** · **Partial** (documented tradeoff) · **Optional** (not required for demo)

---

## Part A — Use cases (proposal numbering)

| # | Item | Status | Notes |
|---|------|--------|--------|
| UC-1 | Register with email verification | **Done** | `require_email_verification` + token table + `/api/auth/verify-email`; SMTP optional (link logged when unset). Default off in dev/tests. |
| UC-2 | Login, logout, JWT, roles | **Done** | |
| UC-3 | Abstractive summary (text) | **Partial** | FLAN-T5 when installed; AWS production uses extractive (120s App Runner limit). User can pick **Abstractive** vs **Concise** in UI. |
| UC-4 | Upload PDF/DOCX/TXT | **Done** | |
| UC-5 | Length + abstractive vs concise | **Done** | `summary_style` on API + Summarize page. |
| UC-6 | View, copy, download | **Done** | |
| UC-7 | History + search | **Done** | |
| UC-8 | Delete summaries | **Done** | |
| UC-9 | Rate summaries | **Done** | Ratings stored; not auto-retrain (see UC-16 job). |
| UC-10 | Admin usage dashboard | **Done** | |
| UC-11 | Admin user/role management | **Done** | |
| UC-12 | Approve/promote model version | **Done** | `ModelVersion`, admin API + UI, migration `0002_model_lifecycle`. |
| UC-13 | CI lint + tests | **Done** | |
| UC-14 | CD to AWS | **Done** | ECR + App Runner live. |
| UC-15 | CloudWatch + failure alerts | **Partial** | Logs to CloudWatch; **alarms + SNS** in `infra/terraform/monitoring.tf` (enable via `enable_cloudwatch_alarms`). Subscribe email to SNS in AWS console. |
| UC-16 | Retraining / register version | **Done** | `POST /api/admin/training-jobs` runs ROUGE evaluation and registers a pending version. |

---

## Part B — Technology rows

| # | Item | Status |
|---|------|--------|
| 1 | UML / use cases | **Done** — `docs/use-cases.md`, `docs/uml-diagrams.md` |
| 2 | 12+ use cases, business classes | **Done** — includes `ModelVersion`, `TrainingJob` |
| 3 | Three tiers | **Done** |
| 4 | Design patterns | **Done** |
| 5 | OpenAPI docs | **Done** — `/docs` live |
| 6 | PostgreSQL schema | **Done** |
| 7 | Unit tests | **Done** — 171+ pytest |
| 8 | Code ↔ diagrams | **Done** (verify before viva) |
| 9 | Docker, CI/CD, App Runner | **Done** — live |
| 10 | Terraform, IAM, monitoring | **Partial** — Terraform + IAM live; alarms in repo; OIDC preferred over static keys |
| 11 | FLAN-T5 + ROUGE evaluation | **Done** — ROUGE in `app/ml/rouge.py`; training job compares candidate vs **extractive baseline** (proposal DistilBART-class reference). Full DistilBART model not bundled (size/GPU). |

---

## Initial demo checklist

| Item | Status |
|------|--------|
| Authentication | **Done** |
| Document upload | **Done** |
| AI summarization | **Partial on AWS** — extractive live; abstractive local / user-selected |
| Database on AWS | **Done** |
| AWS deployment | **Done** |

---

## Enable email verification (production)

Set in App Runner / `.env`:

```env
REQUIRE_EMAIL_VERIFICATION=true
PUBLIC_APP_URL=https://asqmhsdwfs.us-east-2.awsapprunner.com
# Optional SMTP_* for real email delivery
```

---

## Apply CloudWatch alarms

```bash
cd infra/terraform
terraform apply -var="enable_cloudwatch_alarms=true"
# Subscribe your email to the SNS topic in AWS Console
```
