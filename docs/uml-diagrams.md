# UML diagrams

Every diagram here reflects the code as implemented — the class names, attributes and method
names match the source files. Mermaid renders directly on GitHub.

---

## 1. Use case diagram

```mermaid
flowchart LR
    USER(("Registered<br/>user"))
    ADMIN(("Administrator"))
    CI(("CI pipeline"))
    MODEL[["FLAN-T5<br/>(supporting actor)"]]

    subgraph platform["CloudMLOps platform"]
        UC1["UC-01 Register"]
        UC2["UC-02 Log in"]
        UC3["UC-03 Log out"]
        UC4["UC-04 Submit raw text"]
        UC5["UC-05 Upload document"]
        UC6["UC-06 Generate summary"]
        UC7["UC-07 Select summary length"]
        UC8["UC-08 View summary"]
        UC9["UC-09 Download summary"]
        UC10["UC-10 View history"]
        UC11["UC-11 Search history"]
        UC12["UC-12 Delete summary"]
        UC13["UC-13 Rate summary"]
        UC14["UC-14 Manage users"]
        UC15["UC-15 Monitor usage"]
        UC16["UC-16 Automated testing"]
    end

    USER --- UC1
    USER --- UC2
    USER --- UC3
    USER --- UC4
    USER --- UC5
    USER --- UC6
    USER --- UC8
    USER --- UC9
    USER --- UC10
    USER --- UC11
    USER --- UC12
    USER --- UC13

    ADMIN --- UC2
    ADMIN --- UC14
    ADMIN --- UC15

    CI --- UC16

    UC4 -. "«include»" .-> UC6
    UC5 -. "«include»" .-> UC6
    UC6 -. "«include»" .-> UC7
    UC6 --> MODEL
    UC10 -. "«extend»" .-> UC11
    UC8 -. "«extend»" .-> UC9
    UC8 -. "«extend»" .-> UC13
```

---

## 2. Domain class diagram (data tier)

```mermaid
classDiagram
    direction TB

    class User {
        +UUID id
        +str name
        +str email
        +str password_hash
        +UserRole role
        +bool is_active
        +datetime created_at
        +is_admin() bool
    }

    class Session {
        +UUID id
        +UUID user_id
        +str token_id
        +datetime expires_at
        +bool revoked
        +str user_agent
        +str ip_address
        +datetime created_at
        +is_valid() bool
    }

    class Document {
        +UUID id
        +UUID user_id
        +str filename
        +FileType file_type
        +str storage_path
        +int size_bytes
        +int page_count
        +int word_count
        +str extracted_text
        +datetime created_at
        +character_count() int
    }

    class SummaryRequest {
        +UUID id
        +UUID user_id
        +UUID document_id
        +SourceType source_type
        +SummaryLength summary_length
        +str title
        +str input_text
        +int input_word_count
        +RequestStatus status
        +str error_message
        +datetime created_at
    }

    class Summary {
        +UUID id
        +UUID request_id
        +str summary_text
        +int word_count
        +float compression_ratio
        +float processing_time_seconds
        +str model_name
        +str backend
        +int chunk_count
        +datetime created_at
    }

    class FeedbackRecord {
        +UUID id
        +UUID summary_id
        +UUID user_id
        +int rating
        +str comment
        +datetime created_at
    }

    class UsageMetric {
        +UUID id
        +UUID user_id
        +MetricType metric_type
        +bool success
        +float duration_seconds
        +str detail
        +dict attributes
        +datetime created_at
    }

    User "1" --> "0..*" Session : issues
    User "1" --> "0..*" Document : uploads
    User "1" --> "0..*" SummaryRequest : submits
    User "1" --> "0..*" FeedbackRecord : writes
    User "1" --> "0..*" UsageMetric : generates
    Document "0..1" --> "0..*" SummaryRequest : is source of
    SummaryRequest "1" --> "0..1" Summary : produces
    Summary "1" --> "0..*" FeedbackRecord : is rated by
```

---

## 3. Business tier class diagram

Eight services plus the AI abstractions. Note that no service depends on FastAPI.

```mermaid
classDiagram
    direction LR

    class AuthService {
        -UserRepository users
        -SessionRepository sessions
        -MetricRepository metrics
        +register(payload, role) User
        +login(payload, user_agent, ip) tuple
        +logout(token) bool
        +resolve_token(token) User
        +ensure_admin_account() User
    }

    class DocumentService {
        -DocumentRepository documents
        -MetricRepository metrics
        -ExtractionService extraction
        +upload(user, filename, content_type, data) Document
        +get_owned(user, document_id) Document
        +list_for_user(user, limit, offset) tuple
        +delete(user, document_id) void
    }

    class ExtractionService {
        +extract(file_type, data) ExtractionResult
        +extract_from_filename(filename, data) ExtractionResult
    }

    class SummarizationService {
        -SummaryRequestRepository requests
        -SummaryRepository summaries
        -DocumentRepository documents
        -MetricRepository metrics
        -Summarizer summarizer
        +summarize_text(user, text, length, title) Summary
        +summarize_document(user, document_id, length, title) Summary
        +get_owned_summary(user, summary_id) Summary
        +build_download_text(summary) str
        -_run(user, request, metric_type) Summary
        -_validate_input(text, source) str
    }

    class HistoryService {
        -SummaryRepository summaries
        -FeedbackRepository feedback
        +list_history(user, search, limit, offset) tuple
        +get_detail(user, summary_id) SummaryDetailResponse
        +delete(user, summary_id) void
    }

    class FeedbackService {
        -FeedbackRepository feedback
        -SummaryRepository summaries
        -MetricRepository metrics
        +submit(user, payload) FeedbackRecord
        +list_for_summary(user, summary_id) list
    }

    class AdminService {
        -UserRepository users
        -SessionRepository sessions
        -SummaryRepository summaries
        -FeedbackRepository feedback
        -MetricRepository metrics
        +list_users(search, role, limit, offset) tuple
        +set_active(admin, user_id, is_active) User
        +set_role(admin, user_id, role) User
        +platform_stats() PlatformStatsResponse
        +usage_metrics(days) UsageMetricsResponse
        +quality_metrics() QualityMetricsResponse
    }

    class BaseRepository~ModelT~ {
        <<abstract>>
        #Session db
        +add(entity) ModelT
        +create(**fields) ModelT
        +delete(entity) void
        +get(entity_id) ModelT
        +count() int
    }

    AuthService ..> BaseRepository
    DocumentService ..> BaseRepository
    DocumentService --> ExtractionService
    SummarizationService ..> BaseRepository
    HistoryService ..> BaseRepository
    FeedbackService ..> BaseRepository
    AdminService ..> BaseRepository
```

### AI tier — Strategy and Factory

```mermaid
classDiagram
    direction TB

    class Summarizer {
        <<abstract>>
        +str backend
        +model_name() str
        +is_ready() bool
        +warmup() void
        +summarize(text, strategy)* SummarizationOutput
    }

    class FlanT5Summarizer {
        -ModelLoader _loader
        +summarize(text, strategy) SummarizationOutput
        -_generate(prompt, strategy) str
    }

    class ExtractiveSummarizer {
        +summarize(text, strategy) SummarizationOutput
        -_term_frequencies(text) dict
        -_score(sentence, frequencies, index, total) float
    }

    class ModelLoader {
        <<singleton>>
        -LoadedModel _loaded
        -Lock _lock
        +instance() ModelLoader
        +load() LoadedModel
        +is_loaded() bool
    }

    class SummaryLengthStrategy {
        <<abstract>>
        +SummaryLength length
        +str label
        +int target_words
        +int chunk_max_words
        +params()* GenerationParams
        +instruction()* str
        +build_prompt(text) str
        +build_reduce_prompt(partials) str
    }

    class ShortSummaryStrategy {
        +target_words = 55
    }
    class MediumSummaryStrategy {
        +target_words = 130
    }
    class LongSummaryStrategy {
        +target_words = 260
    }

    class SummaryStrategyFactory {
        <<factory>>
        +create(length) SummaryLengthStrategy
        +available() list
    }

    class SummarizerFactory {
        <<factory>>
        +resolve_backend(requested) str
        +create_summarizer(requested) Summarizer
        +get_summarizer() Summarizer
        +set_summarizer(summarizer) void
    }

    Summarizer <|-- FlanT5Summarizer
    Summarizer <|-- ExtractiveSummarizer
    FlanT5Summarizer --> ModelLoader
    SummaryLengthStrategy <|-- ShortSummaryStrategy
    SummaryLengthStrategy <|-- MediumSummaryStrategy
    SummaryLengthStrategy <|-- LongSummaryStrategy
    SummaryStrategyFactory ..> SummaryLengthStrategy : creates
    SummarizerFactory ..> Summarizer : creates
    Summarizer ..> SummaryLengthStrategy : uses
```

### Document extraction — Factory

```mermaid
classDiagram
    direction TB

    class TextExtractor {
        <<abstract>>
        +FileType file_type
        +extract(data) ExtractionResult
        -_parse(data)* ExtractionResult
    }

    class PdfExtractor {
        +file_type = PDF
        -_parse(data) ExtractionResult
    }
    class DocxExtractor {
        +file_type = DOCX
        -_parse(data) ExtractionResult
    }
    class TxtExtractor {
        +file_type = TXT
        -_parse(data) ExtractionResult
    }

    class DocumentExtractorFactory {
        <<factory>>
        -dict _registry
        +register(file_type, extractor) void
        +create(file_type) TextExtractor
        +create_for_filename(filename) TextExtractor
        +supported_types() list
    }

    class ExtractionResult {
        +str text
        +int page_count
        +word_count() int
        +character_count() int
    }

    TextExtractor <|-- PdfExtractor
    TextExtractor <|-- DocxExtractor
    TextExtractor <|-- TxtExtractor
    DocumentExtractorFactory ..> TextExtractor : creates
    TextExtractor ..> ExtractionResult : returns
```

---

## 4. Sequence — login (UC-02)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as React (Login)
    participant API as POST /api/auth/login
    participant S as AuthService
    participant UR as UserRepository
    participant SR as SessionRepository
    participant DB as PostgreSQL

    U->>R: enter email + password
    R->>API: {email, password}
    API->>S: login(payload, user_agent, ip)
    S->>UR: get_by_email(email)
    UR->>DB: SELECT … WHERE lower(email) = ?
    DB-->>UR: User | None

    alt no user or wrong password
        S->>S: verify_password fails
        S->>DB: INSERT usage_metrics (login, success=false)
        S-->>API: AuthenticationError
        API-->>R: 401 "Incorrect email or password."
        Note over API,R: Identical response either way,<br/>so emails cannot be enumerated
    else account deactivated
        S-->>API: PermissionDeniedError
        API-->>R: 403 "This account has been deactivated"
    else valid
        S->>S: create_access_token(user.id, role) → token, exp, jti
        S->>SR: create(user_id, token_id=jti, expires_at)
        S->>DB: INSERT sessions + usage_metrics, COMMIT
        S-->>API: (token, expires_at, user)
        API-->>R: 200 {access_token, expires_at, user}
        R->>R: store token, set AuthContext
        R-->>U: redirect to /dashboard
    end
```

---

## 5. Sequence — document upload (UC-05)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as React (FileUpload)
    participant API as POST /api/documents/upload
    participant D as DocumentService
    participant V as validate_upload
    participant F as DocumentExtractorFactory
    participant E as PdfExtractor
    participant DR as DocumentRepository
    participant FS as File storage
    participant DB as PostgreSQL

    U->>R: drop report.pdf
    R->>R: pre-check extension + size
    R->>API: multipart/form-data
    API->>API: read at most MAX_UPLOAD_SIZE + 1 bytes
    alt over the limit
        API-->>R: 413 payload_too_large
    end
    API->>D: upload(user, filename, content_type, data)
    D->>V: validate extension, MIME, size, magic bytes
    alt validation fails
        V-->>D: UnsupportedFileTypeError
        D->>DB: INSERT usage_metrics (upload, success=false)
        D-->>API: error
        API-->>R: 415 / 422 with a readable message
    else valid
        D->>F: create(FileType.PDF)
        F-->>D: PdfExtractor
        D->>E: extract(data)
        E->>E: PyMuPDF page.get_text() per page
        E->>E: normalize_text()
        alt no text layer (scanned)
            E-->>D: ExtractionError
            API-->>R: 422 "No readable text was found"
        else text extracted
            E-->>D: ExtractionResult(text, page_count)
            D->>FS: write sanitized, random-prefixed filename
            D->>DR: create(document row + extracted text)
            D->>DB: INSERT documents + usage_metrics, COMMIT
            D-->>API: Document
            API-->>R: 201 {id, filename, word_count, text_preview}
        end
    end
```

---

## 6. Sequence — AI summarization (UC-06 / UC-07)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as React (Summarize)
    participant API as POST /api/summaries/text
    participant S as SummarizationService
    participant SF as SummaryStrategyFactory
    participant SUM as FlanT5Summarizer
    participant ML as ModelLoader
    participant T as FLAN-T5
    participant DB as PostgreSQL

    U->>R: paste text, pick "medium", Generate
    R->>API: {text, summary_length: "medium"}
    API->>S: summarize_text(user, text, MEDIUM)
    S->>S: _validate_input → normalize, require ≥ 200 chars
    S->>DB: INSERT summary_requests (status = pending)

    S->>SF: create("medium")
    SF-->>S: MediumSummaryStrategy

    S->>SUM: summarize(text, strategy)
    SUM->>SUM: chunk_text(max_words = 380)
    SUM->>ML: load()
    alt first request in this process
        ML->>T: from_pretrained (cached after this)
    end
    ML-->>SUM: tokenizer + model

    loop map: each chunk
        SUM->>T: generate(strategy.build_prompt(chunk))
        T-->>SUM: partial summary
    end
    loop reduce: while > 1 partial, max 3 rounds
        SUM->>T: generate(strategy.build_reduce_prompt(partials))
        T-->>SUM: merged summary
    end
    SUM-->>S: SummarizationOutput(text, chunk_count, model, backend)

    alt generation failed
        S->>DB: UPDATE summary_requests SET status='failed', error_message
        S->>DB: INSERT usage_metrics (success = false), COMMIT
        S-->>API: SummarizationError
        API-->>R: 503 summarization_failed
    else success
        S->>DB: INSERT summaries (words, compression, elapsed)
        S->>DB: UPDATE summary_requests SET status='completed'
        S->>DB: INSERT usage_metrics (success = true), COMMIT
        S-->>API: Summary
        API-->>R: 201 SummaryResponse
        R-->>U: render summary + copy / download / rate
    end
```

---

## 7. Sequence — history search and delete (UC-11 / UC-12)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as React (History)
    participant API as /api/history
    participant H as HistoryService
    participant SR as SummaryRepository
    participant FR as FeedbackRepository
    participant DB as PostgreSQL

    U->>R: type "finance"
    R->>R: debounce 350 ms
    R->>API: GET /api/history?search=finance&page=1&page_size=6
    API->>H: list_history(user, search, limit, offset)
    H->>SR: search_history(user_id, search, limit, offset)
    SR->>DB: SELECT … JOIN summary_requests<br/>WHERE user_id = ? AND (title/summary/input ILIKE ?)<br/>ORDER BY created_at DESC LIMIT/OFFSET
    Note over SR,DB: user_id is part of the query,<br/>so other users' rows are unreachable
    DB-->>SR: rows + total count
    loop each row
        H->>FR: get_by_summary_and_user → my_rating
    end
    H-->>API: (items, total)
    API-->>R: Page{items, total, page, pages}
    R-->>U: render cards + pagination

    U->>R: click delete, confirm
    R->>API: DELETE /api/history/{summary_id}
    API->>H: delete(user, summary_id)
    H->>SR: get_for_user(summary_id, user_id)
    alt not found or not the owner
        H-->>API: NotFoundError
        API-->>R: 404
    else owner
        H->>DB: DELETE summary_requests<br/>(cascades to summaries and feedback_records)
        H-->>API: ok
        API-->>R: 200 {"message": "Summary deleted."}
        R->>API: reload the current page
    end
```

---

## 8. Entity relationship diagram

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : "issues"
    USERS ||--o{ DOCUMENTS : "uploads"
    USERS ||--o{ SUMMARY_REQUESTS : "submits"
    USERS ||--o{ FEEDBACK_RECORDS : "writes"
    USERS ||--o{ USAGE_METRICS : "generates"
    DOCUMENTS ||--o{ SUMMARY_REQUESTS : "is source of"
    SUMMARY_REQUESTS ||--|| SUMMARIES : "produces"
    SUMMARIES ||--o{ FEEDBACK_RECORDS : "is rated by"

    USERS {
        uuid id PK
        varchar name
        varchar email UK
        varchar password_hash
        varchar role "user | admin"
        boolean is_active
        timestamptz created_at
    }

    SESSIONS {
        uuid id PK
        uuid user_id FK
        varchar token_id UK "JWT jti, not the token"
        timestamptz expires_at
        boolean revoked
        varchar user_agent
        varchar ip_address
        timestamptz created_at
    }

    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        varchar filename
        varchar file_type "pdf | docx | txt"
        varchar storage_path
        integer size_bytes
        integer page_count
        integer word_count
        text extracted_text
        timestamptz created_at
    }

    SUMMARY_REQUESTS {
        uuid id PK
        uuid user_id FK
        uuid document_id FK "nullable for pasted text"
        varchar source_type "text | document"
        varchar summary_length "short | medium | long"
        varchar title
        text input_text
        integer input_word_count
        varchar status "pending | completed | failed"
        varchar error_message
        timestamptz created_at
    }

    SUMMARIES {
        uuid id PK
        uuid request_id FK,UK
        text summary_text
        integer word_count
        double compression_ratio
        double processing_time_seconds
        varchar model_name
        varchar backend
        integer chunk_count
        timestamptz created_at
    }

    FEEDBACK_RECORDS {
        uuid id PK
        uuid summary_id FK
        uuid user_id FK
        integer rating "CHECK 1..5"
        varchar comment
        timestamptz created_at
    }

    USAGE_METRICS {
        uuid id PK
        uuid user_id FK
        varchar metric_type
        boolean success
        double duration_seconds
        varchar detail
        json attributes
        timestamptz created_at
    }
```

### Normalization notes

The schema is in third normal form:

- Every table has a single-column UUID primary key and no repeating groups (1NF).
- No non-key column depends on part of a key, because no table has a composite key (2NF).
- No non-key column depends on another non-key column (3NF). In particular, derived values
  like `word_count` and `compression_ratio` are stored on `summaries` deliberately: they are
  a **snapshot of what the model produced at that moment**, not a function of the current
  `summary_text`, so recomputing them later could silently change history.
- `feedback_records` carries `UNIQUE (summary_id, user_id)`, which is what makes re-rating an
  update instead of a duplicate row.
