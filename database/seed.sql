-- =============================================================================
-- Reference data.
--
-- Demo *accounts* are intentionally NOT created here. Passwords must be hashed
-- with the same bcrypt configuration the application uses, and committing a
-- password hash to version control is a bad habit even for a demo. Use the
-- seeding script instead, which hashes credentials at run time:
--
--     cd backend
--     python -m scripts.seed_demo
--
-- The application also creates its own administrator on first boot when
-- SEED_ADMIN=true (see ADMIN_EMAIL / ADMIN_PASSWORD in .env).
--
-- This file holds only data that carries no credentials, and is safe to run
-- repeatedly against a database that already has schema.sql applied.
-- =============================================================================

BEGIN;

-- Nothing in the current data model requires static lookup rows: the enum-like
-- columns (role, file_type, summary_length, status, metric_type) are enforced
-- with CHECK constraints rather than reference tables, which keeps the schema
-- in third normal form without extra joins on every read.
--
-- Kept as a placeholder so the data tier has an obvious home for reference
-- data if a future migration introduces it.

COMMIT;
