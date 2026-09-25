# CloudMLOps — Viva questions and answers

Short spoken answers. Live URLs: UI https://asqmhsdwfs.us-east-2.awsapprunner.com · API https://p3jivcdmbf.us-east-2.awsapprunner.com/docs

---

## Overview

**Q: What is CloudMLOps?**  
A: A three-tier AI platform that summarizes PDF/DOCX/TXT (or pasted text), stores results in PostgreSQL, and supports history, ratings, and admin/MLOps features on AWS App Runner.

**Q: Why three tiers?**  
A: React for UI, FastAPI for business logic and AI orchestration, PostgreSQL for durable data—clear separation and the same model locally (Docker) and in AWS.

**Q: What is live in production?**  
A: Separate App Runner services for frontend and API in `us-east-2`, RDS PostgreSQL, health at `/health`, Swagger at `/docs`.

---

## AI

**Q: Which summarization backends?**  
A: **FLAN-T5-small** when Transformers/Torch are available (typical local Docker); **extractive** summarizer on AWS for speed and App Runner’s ~120s HTTP limit.

**Q: How is the backend chosen?**  
A: `AI_BACKEND` env and `app/ai/factory.py`—`auto` prefers FLAN-T5 if installed, else extractive.

**Q: Long documents?**  
A: Chunking, summarize per chunk, merge; metadata returned (word count, compression, time, chunks).

---

## Stack (why)

**Q: Why FastAPI?**  
A: Validation, OpenAPI/Swagger, performance, Python ML ecosystem.

**Q: Why PostgreSQL?**  
A: Relational users, documents, summaries, feedback, metrics, model versions; migrations via Alembic.

**Q: Why Docker + GitHub Actions?**  
A: Same image from dev to CI to ECR/App Runner; automated tests before deploy.

---

## Security

**Q: Authentication?**  
A: JWT after login; bcrypt password hashing; admin-only routes for admin dashboard and model lifecycle.

---

## MLOps / use cases

**Q: Model lifecycle?**  
A: Admin APIs to list model versions, ROUGE evaluation, approve and promote; training job registration. See `backend/app/api/model_lifecycle.py`.

**Q: UC-12 in use-cases.md vs model lifecycle?**  
A: In `docs/use-cases.md`, UC-12 is **delete summary**; model registry is an extra admin/MLOps extension documented in `deployment-status.md`.

---

## Testing

**Q: How do you ensure quality?**  
A: ~171 pytest tests (auth, uploads, summarization, admin, migrations, ROUGE); Ruff in CI; Postgres job in GitHub Actions.

---

## Challenges

**Q: Main challenge?**  
A: Running transformer inference in cost-bounded cloud within timeouts—addressed with extractive production policy and factory-based switching.

**Q: Future work?**  
A: GPU hosting for full abstractive at scale, stronger CloudWatch alerting, deeper offline benchmarks.

---

## Demo

**Q: Prove it works.**  
A: Open AWS UI, login, summarize, show history; open Swagger and `/health`; show GitHub Actions and repo structure.
