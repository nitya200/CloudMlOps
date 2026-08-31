# Use cases

Sixteen use cases, each traced to the endpoint that exposes it, the service that implements
it and the tests that verify it.

| # | Use case | Actor | Endpoint | Service | Tests |
|---|---|---|---|---|---|
| UC-01 | Register an account | User | `POST /api/auth/register` | `AuthService.register` | `test_auth.py::TestRegistration` |
| UC-02 | Log in | User, Admin | `POST /api/auth/login` | `AuthService.login` | `test_auth.py::TestLogin` |
| UC-03 | Log out | User, Admin | `POST /api/auth/logout` | `AuthService.logout` | `test_auth.py::TestLogout` |
| UC-04 | Submit raw text | User | `POST /api/summaries/text` | `SummarizationService.summarize_text` | `test_summarization.py::TestSummarizeText` |
| UC-05 | Upload a document | User | `POST /api/documents/upload` | `DocumentService.upload` | `test_documents.py::TestUpload` |
| UC-06 | Generate a summary | User | `POST /api/summaries/text`, `POST /api/summaries/document/{id}` | `SummarizationService` | `test_summarization.py` |
| UC-07 | Select summary length | User | `summary_length` on both summarize endpoints | `SummaryStrategyFactory` | `test_summarization.py::TestStrategyFactory` |
| UC-08 | View a summary | User | `GET /api/summaries/{id}` | `HistoryService.get_detail` | `test_summarization.py::TestSummaryRead` |
| UC-09 | Download a summary | User | `GET /api/summaries/{id}/download` | `SummarizationService.build_download_text` | `test_summarization.py::TestSummaryRead` |
| UC-10 | View summary history | User | `GET /api/history` | `HistoryService.list_history` | `test_history.py::TestListHistory` |
| UC-11 | Search history | User | `GET /api/history?search=` | `SummaryRepository.search_history` | `test_history.py::TestSearchHistory` |
| UC-12 | Delete a summary | User | `DELETE /api/history/{id}` | `HistoryService.delete` | `test_history.py::TestDeleteHistory` |
| UC-13 | Rate summary quality | User | `POST /api/feedback` | `FeedbackService.submit` | `test_feedback.py` |
| UC-14 | Manage users and roles | Admin | `GET /api/admin/users`, `PATCH …/status`, `PATCH …/role` | `AdminService` | `test_admin.py::TestUserManagement` |
| UC-15 | Monitor usage and quality | Admin | `GET /api/admin/stats`, `/usage`, `/metrics` | `AdminService` | `test_admin.py::TestReporting` |
| UC-16 | Automated testing and CI | CI pipeline | `.github/workflows/ci.yml` | pytest + ruff + Docker build | the suite itself |

---

## Detailed specifications

### UC-01 — Register an account

**Actor** Prospective user
**Precondition** The email is not already registered.
**Main flow**

1. The user submits name, email and password.
2. The API validates the email format, that the password is at least 8 characters and
   contains a letter and a digit, and that the name is at least 2 characters.
3. `AuthService` normalizes the email to lower case and checks it is unused.
4. The password is hashed with bcrypt over a SHA-256 pre-hash.
5. A `users` row is created with `role = user`, plus a `registration` usage metric.
6. The API returns `201` with the profile — never the password or its hash.

**Alternate flows**
- Email already registered → `409 conflict`.
- Password or email fails validation → `422 validation_error`.
- A `role` field in the request body is ignored; new accounts are always `user`. Promotion is
  an administrator action (UC-14).

---

### UC-02 — Log in

**Main flow**

1. The user submits email and password.
2. The password is verified against the stored bcrypt hash.
3. A JWT is signed with `sub`, `role`, `iat`, `exp` and a random `jti`.
4. A `sessions` row is written keyed on the `jti`, along with the user agent and client IP.
5. The API returns the token, its expiry and the user profile.

**Alternate flows**
- Unknown email **or** wrong password → `401` with an identical message and status in both
  cases, so the endpoint cannot be used to discover which emails are registered. A failed
  `login` usage metric is recorded either way.
- Deactivated account → `403`.

**Why a session row exists.** A plain stateless JWT cannot be revoked before it expires.
Storing the `jti` means logout (UC-03) and administrator deactivation (UC-14) take effect on
the very next request.

---

### UC-03 — Log out

1. The client sends its bearer token.
2. `AuthService.logout` decodes it and marks the matching `sessions` row `revoked = true`.
3. The frontend clears its stored token.

Logging out with an already-expired or malformed token still returns `200` — the operation is
idempotent, and there is nothing useful to tell the caller.

---

### UC-04 / UC-06 / UC-07 — Submit text, generate a summary, choose a length

**Precondition** Authenticated; at least 200 characters of text after normalization.
**Main flow**

1. The text is normalized (whitespace collapsed, hyphenated line breaks re-joined) and
   length-checked.
2. A `summary_requests` row is written with `status = pending`, so the attempt is recorded
   before anything can fail.
3. `SummaryStrategyFactory` resolves the requested length to a strategy object carrying its
   prompt instruction and decoder settings.
4. The summarizer chunks the input on sentence boundaries, summarizes each chunk, then folds
   the partial summaries together (up to 3 reduce rounds).
5. A `summaries` row records the text, word count, compression ratio, elapsed time, model
   name, backend and chunk count. The request flips to `completed`.
6. A usage metric is written in the same transaction and the summary is returned as `201`.

**Alternate flows**
- Text shorter than 200 characters or blank → `422`.
- Unknown `summary_length` → `422`.
- Model failure → the request is marked `failed` with the error message, a failed metric is
  recorded, and the API returns `503 summarization_failed`.

---

### UC-05 — Upload a document

**Main flow**

1. The browser pre-checks the extension and size for fast feedback.
2. The API reads at most `MAX_UPLOAD_SIZE_MB + 1` bytes, so an oversized body is detected
   without being buffered in full.
3. `validate_upload` checks the extension against `pdf/docx/txt`, that the file is not empty,
   the size limit, and that the **magic bytes** match the extension. A `.txt` containing NUL
   bytes is rejected as binary.
4. `DocumentExtractorFactory` returns the right extractor; PyMuPDF, python-docx or the
   standard library reads the text. DOCX table cells are included, because tables often carry
   the substance of a report.
5. The text is normalized. If nothing readable came out, the upload fails with a message
   explaining that scanned documents need OCR.
6. The file is written under a sanitized, randomly prefixed name inside a per-user directory,
   and a `documents` row stores the metadata and extracted text.

**Alternate flows** `413` oversized · `415` wrong type or mismatched bytes ·
`422` empty file or no extractable text. Every failure also records a failed usage metric,
so the admin dashboard shows upload problems rather than hiding them.

---

### UC-08 / UC-09 — View and download a summary

`GET /api/summaries/{id}` returns the summary with its request context: title, length,
source, original word count, a 600-character preview of the input and the caller's own
rating. `GET /api/summaries/{id}/download` returns a formatted plain-text report with a
`Content-Disposition` attachment header and records a `summary_download` metric.

Both scope the lookup by `user_id` in SQL. A summary belonging to someone else returns `404`,
not `403`, so the response does not confirm that the id exists.

---

### UC-10 / UC-11 / UC-12 — History, search, delete

`GET /api/history` returns a page of the caller's summaries, newest first, in a standard
envelope (`items`, `total`, `page`, `page_size`, `pages`). `search` matches case-insensitively
against the title, the generated summary and the original input text. `page_size` is capped
at 100 so a client cannot ask for the whole table.

Deleting removes the `summary_requests` row, and the `ON DELETE CASCADE` foreign keys take
the summary and its feedback with it — no orphaned rows, which `test_history.py` asserts
directly.

---

### UC-13 — Rate summary quality

A rating is an integer from 1 to 5 with an optional comment of up to 1000 characters,
validated by the schema, re-checked in the service and constrained again in the database
(`CHECK (rating >= 1 AND rating <= 5)`). `UNIQUE (summary_id, user_id)` means submitting a
second rating updates the first rather than inflating the average. Users can only rate
summaries they generated.

---

### UC-14 — Manage users and roles

Administrators can list users (searchable by name or email, filterable by role), activate or
deactivate an account, and change a role.

Two guard rails prevent an administrator from locking the platform out of its own
administration: you cannot deactivate your own account and you cannot remove your own admin
role (both return `409`). Deactivating a user or changing their role **revokes all of their
sessions immediately**, so a token issued a minute ago stops working on the next request
rather than carrying stale privileges until it expires.

---

### UC-15 — Monitor usage and quality

Every business operation writes a `usage_metrics` row — sign-ins, registrations, uploads,
summarizations, downloads and ratings — with a success flag, a duration and a free-form
`attributes` JSON column so new telemetry does not require a migration.

Three endpoints read that data: `/api/admin/stats` for platform totals,
`/api/admin/usage` for counts by type plus a per-day series, and `/api/admin/metrics` for the
rating distribution and the request success rate. All of them return zeros rather than
dividing by zero on an empty platform, which `test_admin.py` verifies explicitly.

---

### UC-16 — Automated testing and CI

`.github/workflows/ci.yml` runs on every push and pull request:

1. **backend** — `ruff check`, `ruff format --check`, `pytest --cov`.
2. **backend-integration** — applies the schema to a real PostgreSQL 16 service container and
   asserts all seven tables exist, so the ORM mapping is proven against the production engine
   and not just SQLite.
3. **frontend** — `npm ci` and a production Vite build.
4. **docker** — builds both images with GitHub Actions layer caching.
5. **summary** — fails the run if any job failed, giving one required status check.

The test suite substitutes a stub summarizer, so CI never downloads torch or the model
weights and finishes in seconds instead of tens of minutes.
