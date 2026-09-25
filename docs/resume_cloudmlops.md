# CloudMLOps — Resume content (AWS links only)

## Project title

**CloudMLOps — AI Document Summarization Platform**  
Team project · Cloud / MLOps

## Links

| | URL |
|---|---|
| **Repository** | https://github.com/nitya200/CloudMlOps |
| **Live UI (AWS)** | https://asqmhsdwfs.us-east-2.awsapprunner.com |
| **Live API** | https://p3jivcdmbf.us-east-2.awsapprunner.com |
| **Swagger** | https://p3jivcdmbf.us-east-2.awsapprunner.com/docs |
| **Health** | https://p3jivcdmbf.us-east-2.awsapprunner.com/health |

## Summary (2–3 lines)

Full-stack **AI document summarization** platform: users upload **PDF/DOCX/TXT** or paste text; summaries are stored in **PostgreSQL** with history, ratings, and admin analytics. **Three-tier** stack (**React**, **FastAPI**, **PostgreSQL**), production on **AWS App Runner** with **CI/CD** (GitHub Actions → ECR), **Terraform**, and **FLAN-T5** locally / **extractive** summarization on AWS for reliable production latency.

## Bullet points (pick 3–5)

- Built a **three-tier** web app (React, FastAPI, PostgreSQL) for document ingestion, AI summarization, history, feedback, and admin dashboards.
- Deployed production on **AWS App Runner** (`us-east-2`) with separate UI/API services and **RDS PostgreSQL**; Swagger-documented REST API.
- Implemented **CI/CD** with **GitHub Actions**, **Docker**, **Amazon ECR**, and **Terraform**; **171+ pytest** tests with Postgres integration in CI.
- Integrated **FLAN-T5** (local) and **extractive** summarization (AWS) via a configurable factory pattern for cloud timeout limits.
- Added **JWT** authentication, bcrypt hashing, admin APIs, and **MLOps** model registry with **ROUGE** evaluation and approve/promote workflow.

## One-liner

**CloudMLOps** — React/FastAPI/PostgreSQL summarization on AWS App Runner, CI/CD, 171+ tests — https://github.com/nitya200/CloudMlOps

## Skills (optional)

React, Vite, FastAPI, Python, PostgreSQL, SQLAlchemy, Alembic, Docker, GitHub Actions, AWS (App Runner, ECR, RDS, S3), Terraform, PyMuPDF, Transformers/FLAN-T5, pytest, JWT
