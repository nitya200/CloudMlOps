# Architecture

## Three tiers

```mermaid
flowchart TB
    subgraph presentation["Presentation tier — React 19 + Vite"]
        UI["Pages<br/>Login · Register · Dashboard · Summarize<br/>History · SummaryDetails · AdminDashboard"]
        CTX["AuthContext<br/>token + profile state"]
        SVC["Service layer<br/>axios client with auth interceptors"]
        UI --> CTX --> SVC
    end

    subgraph business["Business tier — FastAPI"]
        API["Routers<br/>auth · documents · summaries<br/>history · feedback · admin · health"]
        DEPS["Dependencies<br/>current_user · current_admin · pagination"]
        SERVICES["Services<br/>Auth · Document · Extraction<br/>Summarization · History · Feedback · Admin"]
        AI["AI tier<br/>ModelLoader · Strategies · Summarizers"]
        REPOS["Repositories<br/>User · Session · Document<br/>SummaryRequest · Summary · Feedback · Metric"]
        API --> DEPS
        API --> SERVICES
        SERVICES --> AI
        SERVICES --> REPOS
    end

    subgraph data["Data tier — PostgreSQL 16"]
        DB[("users · sessions · documents<br/>summary_requests · summaries<br/>feedback_records · usage_metrics")]
        FS[["Object storage<br/>uploaded files"]]
    end

    SVC -- "HTTPS / JSON<br/>Bearer JWT" --> API
    REPOS -- SQLAlchemy --> DB
    SERVICES --> FS
```

The dependency arrows only ever point downward. Concretely:

- **Routers** never contain SQL or business rules. They validate the request with a Pydantic
  schema, call one service method and map the result to a response schema.
- **Services** never import FastAPI. They raise domain exceptions from
  `app/core/exceptions.py`, and a single handler in `app/main.py` translates those into HTTP
  status codes. This is why the business rules can be tested without a web server.
- **Repositories** are the only place a SQL query is constructed. Ownership filters live in
  the query itself, not in Python after the fact.

## Request lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant M as Middleware
    participant D as Dependencies
    participant R as Router
    participant S as Service
    participant Repo as Repository
    participant DB as PostgreSQL

    B->>M: POST /api/summaries/text
    M->>M: assign X-Request-ID, start timer
    M->>D: forward
    D->>D: resolve DB session
    D->>DB: load session row for the JWT jti
    DB-->>D: session + user
    D->>R: inject current_user
    R->>R: validate body (Pydantic)
    R->>S: summarize_text(user, text, length)
    S->>Repo: create SummaryRequest (pending)
    S->>S: run the summarizer
    S->>Repo: create Summary, mark request completed
    S->>Repo: record UsageMetric
    Repo->>DB: COMMIT
    S-->>R: Summary
    R-->>M: SummaryResponse (201)
    M->>M: attach X-Request-ID, X-Process-Time, log the line
    M-->>B: JSON
```

Two details worth calling out:

- **The `SummaryRequest` row is written before the model runs.** If generation fails, the row
  is marked `failed` with the error message, so a failure is auditable rather than invisible.
- **Telemetry is written in the same transaction as the business change.** A summary and its
  usage metric commit together, so the admin dashboard can never disagree with the history.

## Data flow through a document upload

```mermaid
flowchart LR
    F["File bytes"] --> V{"validate_upload"}
    V -- "bad extension /<br/>magic bytes /<br/>too large" --> ERR["Domain error<br/>415 · 413 · 422"]
    V -- ok --> FAC["DocumentExtractorFactory"]
    FAC --> P1["PdfExtractor<br/>PyMuPDF"]
    FAC --> P2["DocxExtractor<br/>python-docx"]
    FAC --> P3["TxtExtractor<br/>encoding detection"]
    P1 & P2 & P3 --> N["normalize_text<br/>de-hyphenate, collapse whitespace"]
    N -- "empty" --> ERR2["extraction_failed<br/>scanned PDF, no text layer"]
    N -- "text" --> ST["Store file + extracted text"]
    ST --> DB[("documents")]
```

## Why SQLite in tests and PostgreSQL in production

The models use a `GUID` type decorator (`app/models/base.py`) that maps to a native
PostgreSQL `uuid` column and to `CHAR(36)` everywhere else. Enum columns use
`Enum(..., native_enum=False)`, which produces `VARCHAR` plus a `CHECK` constraint on both
engines. That means one set of models serves both, so the test suite runs in about three
seconds without a database container, while a dedicated CI job still applies the same schema
to a real PostgreSQL 16 instance to prove the mapping holds.

## Scaling and deployment shape

```mermaid
flowchart LR
    GH["GitHub"] --> GA["GitHub Actions<br/>lint · test · build"]
    GA --> ECR["Amazon ECR"]
    ECR --> AR1["App Runner<br/>backend"]
    ECR --> AR2["App Runner<br/>frontend (nginx)"]
    AR1 --> RDS[("Amazon RDS<br/>PostgreSQL")]
    AR1 --> CW["CloudWatch<br/>logs · metrics · alarms"]
    AR2 --> CW
```

The backend container runs **one uvicorn worker**. The model is held in process memory, so a
second worker would double the memory footprint for no throughput gain on a small instance —
scaling out means more instances, not more workers. Generation itself is serialized behind a
lock in `app/ai/flan_t5.py` because a shared transformer module is not safe to drive from
multiple threads at once.

Connection pooling uses `pool_pre_ping=True` and `pool_recycle=1800`, which matters on RDS:
idle connections get dropped, and without pre-ping the first query after an idle period fails.
