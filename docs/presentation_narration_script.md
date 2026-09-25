# CloudMLOps — Viva / Presentation Narration Script

Use this as a spoken script. It is written in **passage form** (full sentences), not bullet
points. Adjust pace to your slot; the full read is roughly ten to twelve minutes.

---

## 1. Opening — what this project is

Good morning. We present **CloudMLOps**, an AI-powered document summarization platform built
as a team project for cloud and MLOps coursework. The idea is simple on the surface and
deliberate underneath: people receive long PDFs, Word files, and plain-text reports, but they
rarely have time to read every page. Our system lets a user sign in, upload a document or paste
text, choose how short the summary should be, and receive a concise answer in seconds. Every
summary is stored in a database so the user can search history, download results, and rate
quality. Administrators can see usage, manage accounts, and—where our proposal required
it—run a small **model lifecycle** workflow: register a model version, evaluate it with ROUGE
scores, approve it, and promote it to production.

What makes this a **Cloud MLOps** project rather than a demo script is that we did not stop at
the application. We containerized the services, wired **GitHub Actions** for continuous
integration and deployment, pushed images to **Amazon ECR**, and run the live product on
**AWS App Runner** in `us-east-2` with **PostgreSQL on RDS**, optional object storage for
uploads, and health checks you can open in a browser during this presentation. We also keep a
zero-cost reference deployment on **Netlify** and **Render** so reviewers can try the same UI
without AWS credentials.

Our live AWS frontend is at
`https://asqmhsdwfs.us-east-2.awsapprunner.com`, and the production API—including Swagger
documentation—is at `https://p3jivcdmbf.us-east-2.awsapprunner.com`. The repository is public
on GitHub under `nitya200/CloudMlOps`.

---

## 2. Problem we addressed

Organizations and students face the same bottleneck: important information is locked inside
long documents. Copying paragraphs into chat tools is inconsistent, hard to audit, and often
not allowed for confidential material. Teams also need **one place** where extraction,
summarization, storage, and feedback live together, with proper authentication and an admin
view of usage.

On the engineering side, modern summarization models are heavy. A full **FLAN-T5** run on a
small cloud instance can exceed HTTP timeouts—AWS App Runner, for example, enforces a
**120-second** request limit on the path we use. A serious project therefore needs both a
strong local AI story and a **production strategy** that stays reliable in the cloud. We
designed for both instead of pretending one size fits every environment.

---

## 3. Our solution in one flow

From the user’s perspective, the flow is linear. After registration or login, the user opens
the **Summarize** page, either pastes at least two hundred characters of text or uploads a
**PDF, DOCX, or TXT** file within the configured size limit. The backend validates the file,
extracts text with format-specific libraries, selects a summarization strategy, and returns a
summary. The UI shows word counts, compression ratio, processing time, and chunk information
when the document was split. The user can copy the text, download it, or assign a star rating.
All of this is persisted so **History** search and pagination work on real data.

Behind that experience we use a **three-tier architecture**. The **presentation tier** is a
React single-page application. The **business tier** is FastAPI in Python, where auth,
validation, document ingestion, AI orchestration, and admin APIs live. The **data tier** is
PostgreSQL, with Alembic migrations applied in CI and in production. That separation keeps
responsibilities clear, matches what we were asked to deliver academically, and mirrors how
the same codebase is deployed twice: once on AWS for production and once on Render/Netlify as
a teaching-friendly demo.

---

## 4. Technology stack — what we used and why (passage)

### Frontend: React 19, Vite, React Router, Axios

We chose **React** because it is the standard for interactive dashboards and forms: upload
controls, multi-step summarize flows, admin tables, and JWT-aware routing all fit naturally
into components and hooks. **Vite** gives fast local development and optimized production
builds without a heavy toolchain. **React Router** separates public routes (login, register)
from protected routes (dashboard, summarize, history, admin). **Axios** centralizes HTTP calls
to the API with interceptors for tokens and consistent error handling. We did not adopt a large
UI framework on purpose—the app uses a small in-house design system in CSS so the bundle stays
light and the look stays consistent on Netlify and AWS.

### Backend: Python 3.12 and FastAPI

**Python** is the practical choice for document extraction, machine learning libraries, and
rapid API development. **FastAPI** gives automatic OpenAPI documentation—which you can see live
at `/docs` on our API URL—plus Pydantic validation on every request body and clear async
support where we need it. The service layer is organized so routes stay thin and business logic
lives in services and repositories, which also makes the **171 automated tests** easier to
write and maintain.

### Database: PostgreSQL 16, SQLAlchemy 2, Alembic

Summaries, users, documents, ratings, usage metrics, and model-version records must survive
restarts and scale with real usage, so **PostgreSQL** is the right data store. **SQLAlchemy
2.0** maps our domain models with type-safe queries and migration-friendly schemas. **Alembic**
versions the schema—including our **model lifecycle** migration—so CI applies the same
upgrades as production. Tests can run against SQLite for speed, but integration jobs use real
Postgres to catch migration and SQL issues early.

### Document extraction: PyMuPDF, python-docx

Summarization only works if text extraction is trustworthy. **PyMuPDF** handles PDF layout and
encoding edge cases better than naive parsers. **python-docx** reads Word documents structure
aware. Plain text uses the standard library. Keeping extraction in dedicated modules means we
can test them independently—fifteen extraction tests in the suite—and swap strategies without
touching the UI.

### AI tier: Hugging Face Transformers, FLAN-T5, extractive fallback

The academic goal includes **abstractive** summarization via **`google/flan-t5-small`**, loaded
through **Transformers** and **PyTorch** when those dependencies are installed—typically in
local **Docker Compose**, where the model cache persists in a volume. In **production on AWS
App Runner**, we configure the **fast extractive summarizer** so responses stay within the
service timeout and remain predictable on CPU-only instances. That is an honest MLOps decision:
the same factory pattern selects the backend (`ai/factory.py`), local developers get the full
model experience, and cloud users get reliability. The Docker image can still ship FLAN-T5 for
future GPU or larger instances; deployment policy chooses what runs today.

We also implement **Factory** and **Strategy** patterns around prompts and backends so adding
another model later does not rewrite the API surface.

### Security and auth: JWT, bcrypt, role-based admin

Users authenticate with email and password; passwords are hashed with **bcrypt**. **JWT**
tokens identify sessions on subsequent requests. Admin-only routes—usage dashboards, user
management, model approve/promote—check roles before executing. Secrets such as database URLs
and signing keys come from environment variables and, on AWS, **Secrets Manager**, not from
source code.

### DevOps and cloud: Docker, GitHub Actions, ECR, App Runner, Terraform

**Docker** guarantees that what we test is what we ship: one image for the API, one for the
frontend, orchestrated locally with **Docker Compose** alongside Postgres. **GitHub Actions**
runs linting, the full pytest suite, Postgres integration, and Docker builds on every push and
pull request. When credentials are configured on `main`, the pipeline pushes to **Amazon ECR**
and rolls out **App Runner** services. **Terraform** under `infra/terraform/` describes VPC
connector, services, and related AWS resources so infrastructure is repeatable and reviewable,
not a one-off console click. **CloudWatch** collects logs from running services for operations.

We keep **Netlify** for static frontend hosting and **Render** for a free-tier API demo so
faculty and peers can click a link without AWS accounts. Production truth, however, is the AWS
pair listed in our README and deployment status document.

### Testing and quality: pytest, Ruff

**pytest** covers authentication, uploads, summarization paths, admin behavior, migrations,
model lifecycle, and ROUGE utilities—**171 tests** in total at the time this script was
written. **Ruff** enforces Python style in CI. That combination gives us confidence when we
change AI or deployment settings.

---

## 5. Architecture and deployment (how it runs in production)

In production, the browser loads the React app from an App Runner–hosted frontend service.
The SPA calls the FastAPI backend on a separate App Runner URL. The backend connects through
a **VPC connector** to **RDS PostgreSQL**, stores uploaded files in **S3** when configured,
and reads secrets from **Secrets Manager**. CI builds both images, tags them, pushes to ECR,
and triggers deployment. Health endpoint `/health` reports database connectivity; we use that
in smoke checks after every deploy.

This is the same logical architecture as local development—only the hostnames and secret
sources change. That parity is intentional: it reduces “works on my machine” risk and is
exactly what a cloud MLOps course asks you to demonstrate.

---

## 6. MLOps features beyond summarization

Where the proposal asked for advanced use cases, we added **model lifecycle** APIs and admin
UI: register a candidate model version, run **ROUGE**-based evaluation against a small corpus,
approve a version, and promote it so the factory can treat it as the active production model.
That is not theater—the routes, services, repository layer, migration, and tests exist in the
repository. It shows we understand that ML in production is not only inference but also
**governance, evaluation, and promotion**.

---

## 7. Results you can verify live

During Q&A you can open the AWS UI, log in, upload a short PDF or paste text, and show a
summary appearing in the output panel. You can open **History** to prove persistence. On the
API slide, Swagger documents every endpoint. GitHub shows workflows under `.github/workflows`.
If asked about tests, mention the pytest suite and that CI must pass before deploy jobs run
when secrets are present.

---

## 8. Limitations and future work (honest closing)

We are transparent that **AWS production today uses extractive summarization** for speed and
timeout compliance, while **FLAN-T5 abstractive** summarization is the default in local
Docker where GPU or long-running inference is acceptable. Future work—already noted in our
slides—includes GPU-backed App Runner or SageMaker for full abstractive at scale, richer
CloudWatch alarming, and deeper offline benchmarks when more compute is available.

---

## 9. One-paragraph elevator version (if time is short)

CloudMLOps is a three-tier document summarization product: React on the front, FastAPI and
Python in the middle, PostgreSQL at the back, with PDF/DOCX/TXT ingestion and user history.
We use FLAN-T5 locally and a fast extractive path on AWS App Runner so production stays within
cloud timeouts. Docker and GitHub Actions build and deploy images to ECR; Terraform and App
Runner host the live URLs we demo today, with Netlify and Render as a free reference. Admin
features and model lifecycle with ROUGE evaluation complete the MLOps story, backed by 171
automated tests.

---

## 10. Suggested slide order while you speak

| While on slide | Say roughly |
|----------------|-------------|
| Title | Section 1 (first paragraph) |
| Overview / Problem | Sections 2–3 |
| Objectives / Solution | Section 3 |
| Technologies | Section 4 (pick layers relevant to question) |
| Architecture | Section 5 |
| Features / Admin | Section 3 + 6 |
| Interactive Demo | Section 7 — then **click** live URLs |
| Results | Section 7 |
| Future / Conclusion | Section 8 + 9 |
| Thank you | Invite questions; offer live demo again |

---

*Generated from repository facts in `README.md`, `docs/deployment-status.md`, and the current
test suite. Update the test count if you add or remove tests.*
