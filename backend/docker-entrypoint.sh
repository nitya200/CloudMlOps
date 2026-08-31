#!/bin/sh
# Container entrypoint.
#
# Applies database migrations before the API accepts traffic, so a rolling
# deployment can never serve requests against a schema that predates the code.
# Set RUN_MIGRATIONS=false to skip (for example when several instances start at
# once and a separate job owns the migration).
set -e

# Run a one-off command instead of the server when one is given, so admin tasks
# work as you would expect:
#     docker compose run --rm backend alembic stamp head
#     docker compose run --rm backend python -m scripts.seed_demo
# Without this the arguments would be silently ignored and the API would start.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  # App Runner starts the container before RDS finishes accepting connections
  # often enough that a bare `alembic upgrade` is a coin flip.
  attempt=1
  until alembic upgrade head; do
    if [ "$attempt" -ge "${MIGRATION_MAX_ATTEMPTS:-10}" ]; then
      echo "Migrations failed after $attempt attempts; refusing to start." >&2
      exit 1
    fi
    echo "Migration attempt $attempt failed; retrying in 5s..."
    attempt=$((attempt + 1))
    sleep 5
  done
  echo "Migrations applied."
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips '*'
