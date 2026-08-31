-- =============================================================================
-- CloudMLOps - AI Document Summarization Platform
-- PostgreSQL schema (data tier), normalized to 3NF.
--
-- REFERENCE ONLY. Alembic owns the real schema
-- (backend/alembic/versions/); run `alembic upgrade head` to create or update a
-- database. This file is kept for the ER/class diagrams and as readable
-- documentation of the data model.
--
-- Do not apply this file to a database the application also migrates: two
-- sources of truth drift apart, and a mismatch here between the CHECK
-- constraints and the ORM enum values once broke every INSERT in production.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- users: authentication principals and their role
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(120) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'user'
                    CHECK (role IN ('user', 'admin')),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- ---------------------------------------------------------------------------
-- sessions: one row per issued JWT so logout can revoke server side
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_id    VARCHAR(64) NOT NULL UNIQUE,   -- JWT "jti" claim, never the token
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE,
    user_agent  VARCHAR(255),
    ip_address  VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sessions_user_id  ON sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_token_id ON sessions (token_id);

-- ---------------------------------------------------------------------------
-- documents: uploaded files and their extracted text
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    filename        VARCHAR(255) NOT NULL,
    file_type       VARCHAR(10)  NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    storage_path    VARCHAR(512),               -- local path now, S3 key later
    size_bytes      INTEGER      NOT NULL DEFAULT 0,
    page_count      INTEGER,
    word_count      INTEGER      NOT NULL DEFAULT 0,
    extracted_text  TEXT         NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id);

-- ---------------------------------------------------------------------------
-- summary_requests: what the user asked the model to do
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS summary_requests (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    document_id       UUID         REFERENCES documents (id) ON DELETE SET NULL,
    source_type       VARCHAR(20)  NOT NULL CHECK (source_type IN ('text', 'document')),
    summary_length    VARCHAR(20)  NOT NULL DEFAULT 'medium'
                      CHECK (summary_length IN ('short', 'medium', 'long')),
    title             VARCHAR(255) NOT NULL DEFAULT 'Untitled',
    input_text        TEXT         NOT NULL,
    input_word_count  INTEGER      NOT NULL DEFAULT 0,
    status            VARCHAR(20)  NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'completed', 'failed')),
    error_message     VARCHAR(500),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_summary_requests_user_id     ON summary_requests (user_id);
CREATE INDEX IF NOT EXISTS ix_summary_requests_document_id ON summary_requests (document_id);

-- ---------------------------------------------------------------------------
-- summaries: the generated output (1:1 with a request)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS summaries (
    id                       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id               UUID         NOT NULL UNIQUE
                             REFERENCES summary_requests (id) ON DELETE CASCADE,
    summary_text             TEXT         NOT NULL,
    word_count               INTEGER      NOT NULL DEFAULT 0,
    compression_ratio        DOUBLE PRECISION NOT NULL DEFAULT 0,
    processing_time_seconds  DOUBLE PRECISION NOT NULL DEFAULT 0,
    model_name               VARCHAR(120) NOT NULL DEFAULT 'unknown',
    backend                  VARCHAR(40)  NOT NULL DEFAULT 'unknown',
    chunk_count              INTEGER      NOT NULL DEFAULT 1,
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_summaries_request_id ON summaries (request_id);

-- ---------------------------------------------------------------------------
-- feedback_records: 1-5 star quality rating per user per summary
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback_records (
    id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_id  UUID          NOT NULL REFERENCES summaries (id) ON DELETE CASCADE,
    user_id     UUID          NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    rating      INTEGER       NOT NULL,
    comment     VARCHAR(1000),
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_feedback_rating_range CHECK (rating >= 1 AND rating <= 5),
    CONSTRAINT uq_feedback_summary_user UNIQUE (summary_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_feedback_records_summary_id ON feedback_records (summary_id);
CREATE INDEX IF NOT EXISTS ix_feedback_records_user_id    ON feedback_records (user_id);

-- ---------------------------------------------------------------------------
-- usage_metrics: operational telemetry surfaced on the admin dashboard
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usage_metrics (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID         REFERENCES users (id) ON DELETE CASCADE,
    metric_type       VARCHAR(40)  NOT NULL,
    success           BOOLEAN      NOT NULL DEFAULT TRUE,
    duration_seconds  DOUBLE PRECISION NOT NULL DEFAULT 0,
    detail            VARCHAR(500),
    attributes        JSON,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_usage_metrics_user_id     ON usage_metrics (user_id);
CREATE INDEX IF NOT EXISTS ix_usage_metrics_metric_type ON usage_metrics (metric_type);
