# CloudMLOps — AI Document Summarization Platform

A three-tier web application that turns long documents into short, readable summaries.
Users upload a **PDF, DOCX or TXT** file (or paste raw text), a **FLAN-T5** model produces an
abstractive summary, and every result is stored in **PostgreSQL** so it can be searched,
downloaded and rated.

```
React (presentation)  ──►  FastAPI (business)  ──►  PostgreSQL (data)
                                    │
                                    └──►  FLAN-T5-small (abstractive summarization)

Docker  ──►  GitHub Actions  ──►  Amazon ECR  ──►  AWS App Runner  ──►  CloudWatch
```

| | |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, PyJWT, bcrypt |
| **Frontend** | React 19, Vite, React Router, Axios |
| **Database** | PostgreSQL 16 (SQLite in the test suite) |
| **AI** | Hugging Face Transformers, `google/flan-t5-small` |
| **Extraction** | PyMuPDF (PDF), python-docx (DOCX), stdlib (TXT) |
| **Testing** | pytest — 166 tests, 90% statement coverage |
| **Tooling** | Ruff, Docker, Docker Compose, GitHub Actions |

---

## Table of contents

- [Quick start](#quick-start)
- [Sharing with another developer](#sharing-with-another-developer)
- [New here? Read this first](#new-here-read-this-first)
- [Running without Docker](#running-without-docker)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Architecture](#architecture)
- [The AI tier](#the-ai-tier)
- [API overview](#api-overview)
- [Testing](#testing)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

---

## Quick start

The fastest path is Docker Compose, which starts PostgreSQL, the API and the web UI together.

```bash
git clone <your-repo-url> CloudMLOps
cd CloudMLOps

cp .env.example .env          # Windows: copy .env.example .env
# Edit .env and set a real JWT_SECRET_KEY:
#   python -c "import secrets; print(secrets.token_urlsafe(64))"

docker compose up --build
```

| Service | URL |
|---|---|
| Web application | <http://localhost:5173> |
| API docs (Swagger) | <http://localhost:8000/docs> |
| API docs (ReDoc) | <http://localhost:8000/redoc> |
| Health check | <http://localhost:8000/health> |
| PostgreSQL | `localhost:5432` |

The first backend start downloads the FLAN-T5 weights (~300 MB) into a Docker volume; later
starts reuse the cache. Sign in with the administrator account seeded from `.env`
(`ADMIN_EMAIL` / `ADMIN_PASSWORD`), or register a normal account through the UI.

> **Change `ADMIN_PASSWORD` before exposing this to anyone.** The default exists only so a
> fresh database has a reachable admin account.

**Want a faster first build?** `INSTALL_AI=false docker compose up --build` skips the ~200 MB
torch download and runs the extractive fallback summarizer instead (see
[The AI tier](#the-ai-tier)).

---

## Sharing with another developer

The repository includes a distributable archive, **`CloudMLOps.zip`**, at the project root.
Send that file by email, cloud drive, or USB — it is small (~200 KB) because it contains
source code and configuration only, not dependencies or secrets.

### What is in the zip

| Included | Excluded (rebuilt locally) |
|---|---|
| All source code (`backend/`, `frontend/`) | `backend/.venv`, `frontend/node_modules` |
| Docker and CI files | `.git` history |
| Alembic migrations, tests, docs | `.env` (your secrets stay on your machine) |
| `.env.example`, `README.md` | Model weights and upload caches |

The archive extracts to a single **`CloudMLOps/`** folder so unzipping does not scatter
files across the desktop.

### What your friend needs installed

- **Docker Desktop** (Windows or macOS) or Docker Engine + Compose (Linux)
- Nothing else — Python, Node, and PostgreSQL all run inside containers

### Steps for the person receiving the zip

**1. Extract and enter the project**

```bash
# macOS / Linux
unzip CloudMLOps.zip
cd CloudMLOps
```

```powershell
# Windows (PowerShell)
Expand-Archive -Path CloudMLOps.zip -DestinationPath .
cd CloudMLOps
```

**2. Create a local environment file**

There is no `.env` in the zip on purpose. Copy the example and edit it:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

Generate a real secret and paste it into `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set the output as `JWT_SECRET_KEY=...`.

For **Docker Compose**, leave `VITE_API_BASE_URL` **empty** or remove that line from `.env`.
The frontend container proxies `/api` to the backend on the same origin; setting
`http://localhost:8000` works but forces cross-origin requests and is only needed when the
API runs on a different host than the UI.

**3. Start the full stack**

```bash
docker compose up --build
```

The first run downloads Python packages, Node modules, and (by default) the FLAN-T5 model
weights (~500 MB total). Later starts reuse Docker volumes and are much faster.

**4. Open the application**

| What | URL |
|---|---|
| Web UI | <http://localhost:5173> |
| API docs | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |

**5. Sign in**

Use the administrator account from `.env` (defaults in `.env.example`):

- Email: `admin@cloudmlops.app`
- Password: `Admin123!` (change this in `.env` before sharing the running app with anyone)

Or register a normal user account from the login page.

**6. Learn the codebase**

Continue with [New here? Read this first](#new-here-read-this-first) — a step-by-step path
through the architecture, one traced request, the data model, and the tests.

### Faster first run (optional)

If your friend only needs to see the UI and API working, skip the AI download:

```bash
INSTALL_AI=false docker compose up --build
```

Summaries use the lightweight extractive backend instead of FLAN-T5. The API contract is
identical; `/health` reports which backend is active.

### Regenerating the zip (for you)

After you change the project, recreate the archive from the project root. This PowerShell
snippet excludes secrets, virtual environments, and dependency folders:

```powershell
# Run from the project root (the folder that contains backend/, frontend/, README.md)
$root = (Get-Location).Path
$zipPath = Join-Path $root "CloudMLOps.zip"
$excludeDirs = @('.git','.venv','venv','node_modules','dist','__pycache__','.pytest_cache',
                 '.ruff_cache','storage','uploads','hf_cache')
$excludeFiles = @('.env','CloudMLOps.zip')

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$files = Get-ChildItem $root -Recurse -File -Force | Where-Object {
  $rel = $_.FullName.Substring($root.Length + 1)
  ($rel.Split('\') | Where-Object { $excludeDirs -contains $_ }).Count -eq 0 -and
  ($excludeFiles -notcontains $_.Name)
}
$zip = [IO.Compression.ZipFile]::Open($zipPath, 'Create')
foreach ($f in $files) {
  $entry = "CloudMLOps/" + $f.FullName.Substring($root.Length + 1).Replace('\','/')
  [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, $entry, 'Optimal') | Out-Null
}
$zip.Dispose()
Write-Host "Created $zipPath ($('{0:N1}' -f ((Get-Item $zipPath).Length/1KB)) KB)"
```

Prefer sharing via **Git** (GitHub, GitLab, etc.) when the other developer will contribute
code: they get history, branches, and CI. The zip is best for a one-time handoff or review.

> **Do not commit `CloudMLOps.zip` to git.** It is listed in `.gitignore` as a build artifact.

---

## New here? Read this first

The rest of this README is reference material — good for looking things up, bad for building
a mental model. This section is the guided path instead. Budget about two hours for steps 1–5;
after that you should be able to find anything on your own.

### Step 1 — See it work before reading any code (15 min)

Run `docker compose up --build`, then use the app as a user would: register an account,
paste a few paragraphs, generate a summary, rate it, and find it again under History. Upload
a PDF and a DOCX too. Then sign in as the admin (`ADMIN_EMAIL` / `ADMIN_PASSWORD` from
`.env`) and open the admin dashboard.

Do this first. Every abstraction below exists to serve one of the behaviours you just saw,
and they are much easier to justify once you have seen what they produce.

### Step 2 — Learn the one rule that explains the layout (10 min)

The backend is four layers, and **dependencies point in one direction only**:

```
api/  ──►  services/  ──►  repositories/  ──►  models/
```

Each layer has exactly one job, and the constraints are what matter:

| Layer | Does | Must never |
|---|---|---|
| `api/` | Validate input, call one service, shape the response | Contain business rules or SQL |
| `services/` | Business logic, authorization, telemetry | Import FastAPI, or write SQL |
| `repositories/` | Build and run queries | Contain business rules |
| `models/` | SQLAlchemy entities | Know anything above them |

That single rule is why services can be unit-tested without HTTP, and why swapping the
database would not touch business logic. If you are ever unsure where code belongs, ask which
layer's job it is — the answer is usually unambiguous.

### Step 3 — Trace one request end to end (30 min)

Reading a codebase breadth-first rarely works. Follow **one** request through every layer
instead, in this order:

1. [`app/main.py`](backend/app/main.py) — app factory, middleware, and the single error
   handler that turns domain exceptions into HTTP responses.
2. [`app/api/summaries.py`](backend/app/api/summaries.py) — find `POST /api/summaries/text`.
   Note how little it does: validate, delegate, return.
3. [`app/api/deps.py`](backend/app/api/deps.py) — how `CurrentUser` turns a bearer token
   into a `User`, and how the rate-limit dependency is built.
4. [`app/services/summarization_service.py`](backend/app/services/summarization_service.py) —
   the actual orchestration: authorize, summarize, persist, record telemetry.
5. [`app/ai/factory.py`](backend/app/ai/factory.py) and
   [`app/ai/prompts.py`](backend/app/ai/prompts.py) — which backend runs, and how each
   summary length owns its prompt and decoder settings.
6. [`app/repositories/`](backend/app/repositories) — the only place SQL is written.

Then read [`tests/test_summarization.py`](backend/tests/test_summarization.py). The tests are
the executable specification, and they are the fastest way to learn what each layer promises.

### Step 4 — Understand the data model (20 min)

Read [`database/schema.sql`](database/schema.sql) top to bottom — it is annotated and models
seven tables in 3NF. The ER diagram in [`docs/uml-diagrams.md`](docs/uml-diagrams.md) is the
same thing visually.

Two things to internalise:

- **`schema.sql` is documentation, not the source of truth.** Alembic owns the real schema.
  Never apply both to one database; that is precisely how they once drifted apart.
- **A summary request and its summary are separate tables.** A request can fail, and a failed
  request is still a row worth keeping for the admin metrics.

### Step 5 — Run the tests and read two of them (15 min)

```bash
cd backend
pytest                      # 166 tests, ~8 s, no PostgreSQL or model weights needed
```

Then read [`tests/conftest.py`](backend/tests/conftest.py) to see how that speed is achieved:
in-memory SQLite, a deterministic stub summarizer, and a fresh schema per test. Read
[`tests/test_auth.py`](backend/tests/test_auth.py) for what the security guarantees actually
mean in practice.

### Step 6 — Make a change, using the grain of the code

Two worked examples. Both are deliberately chosen because the architecture makes them small:

**Add a new file format (say, `.rtf`)**

1. Add `RTF` to `FileType` in `app/models/enums.py`.
2. Subclass `TextExtractor` in `app/services/extraction_service.py`, alongside
   `PdfExtractor`, `DocxExtractor` and `TxtExtractor`.
3. Register it in `DocumentExtractorFactory` in the same file — no caller changes.
4. Add magic bytes to `MAGIC_PREFIXES` in `app/utils/file_utils.py`.
5. `alembic revision --autogenerate -m "add rtf file type"` — the enum's CHECK constraint
   changed, so this step is **not** optional.
6. Add a case to `tests/test_extraction.py`.

**Add an endpoint**

1. Repository method (if a new query is needed) → 2. service method holding the logic →
3. Pydantic schemas in `app/schemas/` → 4. a thin router function → 5. tests at the service
and HTTP levels.

Write the router last. If it ends up longer than a few lines, logic has leaked upward into
the wrong layer.

### Step 7 — Know where to look

| Question | File |
|---|---|
| What settings exist? | `app/core/config.py` and `.env.example` |
| Why did this request return 409? | `app/core/exceptions.py` (each maps to one status) |
| How is the schema changed? | `backend/alembic/versions/` |
| How does auth actually work? | `app/services/auth_service.py`, `app/core/security.py` |
| What does the API return? | `/docs` when running, or `docs/api-reference.md` |
| Why is the code shaped like this? | `docs/design-patterns.md`, `docs/architecture.md` |
| How does it reach AWS? | `docs/deployment-aws.md`, `.github/workflows/ci.yml` |

### Conventions worth knowing before your first PR

- **Services raise domain exceptions, never `HTTPException`.** One handler in `main.py` maps
  them to status codes, so the business tier stays framework-free.
- **A resource owned by someone else returns `404`, not `403`** — a `403` would confirm the
  id exists.
- **Change a model, add a migration.** CI applies migrations to real PostgreSQL and inserts
  rows, so drift fails the build rather than production.
- **Comments explain *why*, not *what*.** Several in this codebase document a bug that has
  already happened once; leave those in place.
- `ruff check . && ruff format .` before pushing.

---

## Running without Docker

Useful while developing, because both tiers reload on save.

### 1. PostgreSQL

Either run just the database in Docker:

```bash
docker compose up -d postgres
```

…or point `DATABASE_URL` at any PostgreSQL instance you already have.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt          # core application
pip install -r requirements-ai.txt       # FLAN-T5 (optional, ~200 MB)
pip install -r requirements-dev.txt      # pytest + ruff

uvicorn app.main:app --reload --port 8000
```

Because `AUTO_CREATE_SCHEMA` defaults to `true`, startup creates any missing tables, seeds the
administrator account and warms up the model — no migration command needed for a first run.
Once you start *changing* models, switch to Alembic (`AUTO_CREATE_SCHEMA=false` plus
`alembic upgrade head`), since `create_all` adds new tables but never alters existing ones.
See [Database migrations](#database-migrations).

Optionally load demo data:

```bash
python -m scripts.seed_demo
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/health` to
`localhost:8000`, so the browser only ever talks to one origin and CORS never comes into play.

---

## Configuration

Every setting is an environment variable (12-factor), so the same container image runs
locally, in CI and on AWS. `.env.example` documents all of them; the ones that matter most:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local PostgreSQL | SQLAlchemy URL. On AWS this is the RDS endpoint. |
| `AUTO_CREATE_SCHEMA` | `true` | `create_all` on boot. Set `false` and use Alembic outside development. |
| `RUN_MIGRATIONS` | `true` | Container entrypoint runs `alembic upgrade head` before serving. |
| `JWT_SECRET_KEY` | insecure placeholder | **Must be changed.** Signs access tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Token lifetime. |
| `RATE_LIMIT_ENABLED` | `true` | Brute-force protection on the credential endpoints. |
| `LOGIN_RATE_LIMIT` | `10` per 5 min | Login attempts allowed per client IP. |
| `REGISTER_RATE_LIMIT` | `5` per hour | Registrations allowed per client IP. |
| `AI_BACKEND` | `auto` | `auto` \| `flan-t5` \| `extractive`. |
| `AI_MODEL_NAME` | `google/flan-t5-small` | Any seq2seq checkpoint on the Hub. |
| `AI_MAX_INPUT_CHARS` | `60000` | Hard cap so one upload cannot exhaust the container. |
| `STORAGE_BACKEND` | `local` | `local` filesystem or `s3`. App Runner needs `s3`. |
| `S3_BUCKET` | – | Required when `STORAGE_BACKEND=s3`. |
| `MAX_UPLOAD_SIZE_MB` | `10` | Upload size limit. |
| `CORS_ORIGINS` | `localhost:5173` | Comma-separated allowed origins. |
| `LOG_JSON` | `false` | `true` in production so CloudWatch can query the fields. |
| `SEED_ADMIN` | `true` | Create the admin account on first boot. |

### Production refuses to start with insecure defaults

When `ENVIRONMENT=production`, the app validates its own configuration at
startup and **exits** rather than serving with a default `JWT_SECRET_KEY`, a
default `ADMIN_PASSWORD`, a wildcard `CORS_ORIGINS`, or `STORAGE_BACKEND=s3`
without a bucket. Anyone who knows the built-in secret could otherwise mint an
admin token, so this is the one failure the health endpoint is not allowed to
merely report.

### Database migrations

Alembic owns the schema. `database/schema.sql` is reference documentation only —
applying both to one database gives two sources of truth that drift apart.

```bash
cd backend
alembic upgrade head          # apply
alembic downgrade -1          # roll back one revision
alembic revision --autogenerate -m "add x"   # after changing a model
```

The Docker image runs `alembic upgrade head` from its entrypoint before uvicorn
starts, retrying while RDS finishes accepting connections.

---

## Project structure

```
CloudMLOps/
├── backend/
│   ├── app/
│   │   ├── main.py                 # app factory, middleware, error handlers
│   │   ├── api/                    # HTTP routers (thin)
│   │   │   ├── deps.py             #   auth + pagination dependencies
│   │   │   ├── auth.py  documents.py  summaries.py
│   │   │   └── history.py  feedback.py  admin.py  health.py
│   │   ├── services/               # business logic (framework-free)
│   │   │   ├── auth_service.py         summarization_service.py
│   │   │   ├── document_service.py     history_service.py
│   │   │   ├── extraction_service.py   feedback_service.py
│   │   │   └── admin_service.py
│   │   ├── repositories/           # the only place that builds SQL
│   │   ├── models/                 # 7 SQLAlchemy entities
│   │   ├── schemas/                # Pydantic request/response contracts
│   │   ├── ai/                     # model loader, prompt strategies, backends
│   │   ├── core/                   # config, database, security, logging
│   │   └── utils/                  # text/file helpers, validators
│   ├── alembic/versions/           # schema migrations (the source of truth)
│   ├── tests/                      # 166 pytest tests
│   ├── scripts/
│   │   ├── seed_demo.py
│   │   └── verify_postgres.py      # CI: insert a row into every table
│   ├── docker-entrypoint.sh        # migrate, then start uvicorn
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                  # Login, Register, Dashboard, Summarize,
│   │   │                           # History, SummaryDetails, AdminDashboard
│   │   ├── components/             # Navbar, ProtectedRoute, FileUpload, …
│   │   ├── context/AuthContext.jsx
│   │   ├── services/               # axios client + API wrappers
│   │   └── index.css               # design system
│   ├── nginx.conf                  # production SPA + API proxy
│   └── Dockerfile
├── database/
│   ├── schema.sql                  # annotated reference DDL (Alembic owns the real schema)
│   └── seed.sql
├── docs/                           # architecture, UML, API, deployment
├── .github/workflows/ci.yml
├── docker-compose.yml
└── .env.example
```

---

## Architecture

Three tiers, with dependencies pointing in one direction only:

```
HTTP request
    │
    ▼
api/          routers: validate input, call a service, map the response
    │         (no SQL, no business rules)
    ▼
services/     business logic: authorization, orchestration, telemetry
    │         (no FastAPI imports, no raw SQL)
    ▼
repositories/ query construction and persistence
    │
    ▼
models/       SQLAlchemy entities  ──►  PostgreSQL
```

Because services never import FastAPI and repositories are the only place SQL is written,
the business rules can be unit-tested directly and the data tier could be swapped without
touching them.

### Design patterns

| Pattern | Where | Why |
|---|---|---|
| **Repository** | `app/repositories/` | Keeps SQL out of the services and makes them testable. |
| **Factory** | `DocumentExtractorFactory` | Adding a file format means adding one class, not editing callers. |
| **Factory** | `ai/factory.py` | Chooses and caches the summarizer backend. |
| **Strategy** | `ai/prompts.py` | Each summary length owns its prompt and decoder settings. |
| **Dependency injection** | FastAPI `Depends`, service constructors | Lets tests swap the DB session and the summarizer. |
| **Singleton** | `ModelLoader` | Loads the transformer once per process, thread-safely. |

See [`docs/design-patterns.md`](docs/design-patterns.md) for the code walkthrough and
[`docs/uml-diagrams.md`](docs/uml-diagrams.md) for the class and sequence diagrams.

### Security

- **Passwords** — bcrypt (12 rounds) over a SHA-256 pre-hash, so passwords longer than
  bcrypt's 72-byte limit are not silently truncated.
- **Tokens** — JWT with a server-side `sessions` row per token, so logout and
  deactivating a user revoke access *immediately* rather than waiting for expiry.
- **Account enumeration** — a wrong password and an unknown email return byte-identical
  responses.
- **Ownership** — enforced in SQL (`WHERE user_id = :caller`), and a resource owned by
  someone else returns `404`, not `403`, so ids are not confirmed.
- **Uploads** — validated on extension, declared MIME type, byte size **and magic bytes**,
  so a renamed archive or executable is rejected. Filenames are sanitized against path
  traversal and stored under a random prefix.
- **Brute force** — the credential endpoints are rate limited per client IP (not per
  email: keying on the account would let an attacker lock a victim out of their own
  login). Hashing is deliberately slow, but nothing else stops an attacker retrying.
- **Errors** — one handler maps domain exceptions to HTTP; stack traces never reach clients.

> **Known trade-offs**, stated rather than hidden:
>
> - The browser keeps its JWT in `localStorage`, which is readable by any script running
>   on the page. An httpOnly cookie plus CSRF protection would be stronger; `localStorage`
>   was chosen to keep the auth flow legible.
> - Rate-limit counters live in the process, so *N* instances allow *N* times the budget.
>   A shared Redis counter would be exact at the cost of another service to run; the
>   per-instance limit still turns an unbounded online attack into a slow one.

---

## The AI tier

`google/flan-t5-small` is an instruction-tuned sequence-to-sequence model with a **512-token
encoder window** — far smaller than a real document. Long inputs are therefore handled with
map-reduce:

```
document ──► chunk on sentence boundaries (≤ ~400 words each)
             │
             ├─► summarize chunk 1 ─┐
             ├─► summarize chunk 2 ─┤
             └─► summarize chunk N ─┴─► combine ──► summarize again ──► final summary
                                          (repeats up to 3 rounds)
```

Three summary lengths are implemented as Strategy objects (`app/ai/prompts.py`), each owning
its instruction text and generation parameters:

| Length | Target | `max_new_tokens` |
|---|---|---|
| Short | ~55 words | 90 |
| Medium | ~130 words | 200 |
| Long | ~260 words | 380 |

### The extractive fallback

torch is a large dependency and not every machine can spare the memory, so the platform ships
a second backend: a dependency-free extractive summarizer that ranks sentences by normalized
term frequency and returns the best ones in their original order.

`AI_BACKEND=auto` (the default) uses FLAN-T5 when transformers and torch are importable and
falls back to the extractive summarizer when they are not. This is what keeps CI fast and
lets the app run on a laptop that cannot host the model — the API contract is identical
either way, and `/health` and `/api/summaries/options` report which backend is live.

Set `AI_BACKEND=flan-t5` to make a missing model a hard error instead of a silent downgrade.

---

## API overview

Full interactive documentation is generated by FastAPI at `/docs`. Every endpoint below
except registration, login and the health probe requires `Authorization: Bearer <token>`.

### Authentication
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Create an account |
| `POST` | `/api/auth/login` | Exchange credentials for a JWT |
| `POST` | `/api/auth/logout` | Revoke the current token server-side |
| `GET` | `/api/auth/me` | Current user profile |

### Documents
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload a PDF/DOCX/TXT and extract its text |
| `GET` | `/api/documents` | List your documents (paginated) |
| `GET` | `/api/documents/{id}` | One document with its extracted text |
| `DELETE` | `/api/documents/{id}` | Delete a document and its stored file |
| `GET` | `/api/documents/supported-types` | Supported formats and size limit |

### Summarization
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/summaries/text` | Summarize pasted text |
| `POST` | `/api/summaries/document/{id}` | Summarize an uploaded document |
| `GET` | `/api/summaries/{id}` | One summary with its request context |
| `GET` | `/api/summaries/{id}/download` | Download a `.txt` report |
| `GET` | `/api/summaries/options` | Available lengths, active backend and model |

### History, feedback, administration
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/history?search=&page=&page_size=` | Search your summaries, newest first |
| `GET` | `/api/history/{id}` | One history entry |
| `DELETE` | `/api/history/{id}` | Delete a summary |
| `POST` | `/api/feedback` | Rate a summary 1–5 (re-rating updates) |
| `GET` | `/api/admin/users` | List users (admin) |
| `PATCH` | `/api/admin/users/{id}/status` | Activate/deactivate a user (admin) |
| `PATCH` | `/api/admin/users/{id}/role` | Change a user's role (admin) |
| `GET` | `/api/admin/stats` | Platform totals (admin) |
| `GET` | `/api/admin/usage` | Usage by type and per day (admin) |
| `GET` | `/api/admin/metrics` | Rating distribution and success rate (admin) |

Errors share one shape:

```json
{
  "code": "not_found",
  "message": "Summary not found.",
  "details": {},
  "request_id": "a3f9c1e08b2d4a71"
}
```

`request_id` is echoed in the `X-Request-ID` header and included in every log line for that
request, which is what makes a user-reported failure traceable in CloudWatch.

---

## Testing

```bash
cd backend
pytest                                          # 166 tests, ~8 s
pytest --cov=app --cov-report=term-missing      # with coverage
ruff check . && ruff format --check .           # lint + format
```

The suite runs against in-memory SQLite and substitutes a deterministic stub summarizer, so
it needs neither PostgreSQL nor the model weights. Coverage spans:

| Area | Covers |
|---|---|
| `test_auth.py` | Registration, login, logout revocation, enumeration resistance, deactivated accounts |
| `test_documents.py` | PDF/DOCX/TXT uploads, magic-byte mismatches, oversized files, scanned PDFs, path traversal, cross-user access |
| `test_extraction.py` | The extractor factory and each real parser, including corrupt files and encodings |
| `test_summarization.py` | The strategy factory, the extractive backend, both summarize endpoints, model-failure handling |
| `test_history.py` | Ordering, pagination, search, deletion cascade, per-user isolation |
| `test_feedback.py` | Valid and invalid ratings, re-rating, rating someone else's summary |
| `test_admin.py` | Role enforcement, session revocation on deactivation, self-lockout guards, metrics on an empty platform |
| `test_core.py` | Password hashing, JWT lifecycle, filename sanitization, chunking, OpenAPI generation, the production-config guard |
| `test_migrations.py` | The Alembic migration produces exactly the schema the models declare, and reverses cleanly |
| `test_storage.py` | Local and pluggable storage backends, path-traversal refusal, deletes that survive a storage outage |

Test files use real generated PDFs and DOCX files (built with the same libraries the app
parses them with) rather than hand-written byte strings, so the parsers are genuinely
exercised.

### CI

`.github/workflows/ci.yml` runs on every push and pull request:

1. **Backend** — ruff lint, ruff format check, pytest with coverage.
2. **Backend integration** — applies the Alembic migrations to a real PostgreSQL 16
   service container, **writes a row into every table**, asserts the enum columns round
   trip as lowercase, checks the cascade deletes, and proves the migration is reversible.
3. **Frontend** — `npm ci` and a production Vite build.
4. **Docker** — builds both images with layer caching.
5. **Deploy** — on `main` only: pushes both images to ECR over OIDC, rolls out App Runner,
   waits for `RUNNING`, and fails if `/health` does not report `status: "ok"`. Skips
   itself when `AWS_ACCOUNT_ID` is not configured, so forks are unaffected.

> **Why step 2 writes rows.** Creating tables proves very little. A schema mismatch once
> created all seven tables and then rejected every `INSERT`, and the SQLite suite could
> not catch it because SQLite generates its schema *from the same models doing the
> writing*. Only real inserts against real PostgreSQL close that gap.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Tier responsibilities, request lifecycle, data flow |
| [`docs/uml-diagrams.md`](docs/uml-diagrams.md) | Use case, class, ER and four sequence diagrams (Mermaid) |
| [`docs/use-cases.md`](docs/use-cases.md) | All 16 use cases mapped to endpoints, services and tests |
| [`docs/design-patterns.md`](docs/design-patterns.md) | Each pattern with the code that implements it |
| [`docs/api-reference.md`](docs/api-reference.md) | Request/response examples and error codes |
| [`docs/deployment-aws.md`](docs/deployment-aws.md) | ECR, App Runner, RDS and CloudWatch walkthrough |

---

## Troubleshooting

**`/health` reports `"database": "unavailable"`**
PostgreSQL is not reachable. Check `DATABASE_URL` and that the container is healthy
(`docker compose ps`). The API deliberately starts anyway so the health endpoint can explain
the problem instead of the container crash-looping.

**Summaries say `"backend": "extractive"` but I want FLAN-T5**
transformers/torch are not installed in that environment. Run
`pip install -r requirements-ai.txt`, or rebuild the image without
`--build-arg INSTALL_AI=false`.

**The first summary takes 30+ seconds**
The model is being downloaded and loaded. Later requests reuse it. To remove the delay
entirely, bake the weights into the image:
`docker build --build-arg PREFETCH_MODEL=true ./backend`.

**Upload rejected with `unsupported_file_type` even though the extension is right**
The file's magic bytes do not match its extension — most often a `.docx` that is actually a
`.doc`, or a PDF that was renamed. Re-save it in the correct format.

**`413 payload_too_large`**
The file exceeds `MAX_UPLOAD_SIZE_MB`. Raise it in `.env` and, if you are running the Docker
frontend, raise `client_max_body_size` in `frontend/nginx.conf` to match.

**A scanned PDF returns `extraction_failed`**
It has no text layer. This platform does not perform OCR; run the file through an OCR tool
first.

---

## License

MIT. Built as a course project for CIS 5690.
