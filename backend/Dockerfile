# =============================================================================
# CloudMLOps business tier
#
# Build (with FLAN-T5, the default):
#   docker build -t cloudmlops-backend ./backend
#
# Build a slim image that uses the extractive fallback instead of torch:
#   docker build --build-arg INSTALL_AI=false -t cloudmlops-backend ./backend
#
# Bake the model weights into the image so the container needs no network and
# starts instantly (adds roughly 300 MB):
#   docker build --build-arg PREFETCH_MODEL=true -t cloudmlops-backend ./backend
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

# curl is only needed for the container health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies are copied and installed first so that source-only changes hit
# the Docker layer cache instead of reinstalling everything.
COPY requirements.txt requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ARG INSTALL_AI=true
# The default PyPI torch wheel bundles CUDA (several GB). App Runner has no
# GPU, so the CPU-only index is used instead.
RUN if [ "$INSTALL_AI" = "true" ]; then \
      pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        -r requirements-ai.txt ; \
    else \
      echo "Skipping AI dependencies - the extractive fallback will be used." ; \
    fi

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/storage /home/app/.cache/huggingface \
    && chown -R app:app /app /home/app

COPY --chown=app:app . .

# Git on Windows preserves neither the executable bit nor LF endings, and a
# CRLF shebang fails as "no such file or directory" because the kernel looks
# for an interpreter named "/bin/sh\r". .gitattributes should prevent this;
# stripping here means a stray CRLF checkout still produces a working image.
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

USER app

ARG PREFETCH_MODEL=false
ARG AI_MODEL_NAME=google/flan-t5-small
RUN if [ "$PREFETCH_MODEL" = "true" ] && [ "$INSTALL_AI" = "true" ]; then \
      python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
name='${AI_MODEL_NAME}'; AutoTokenizer.from_pretrained(name); \
AutoModelForSeq2SeqLM.from_pretrained(name)" ; \
    fi

ENV STORAGE_DIR=/app/storage \
    ENVIRONMENT=production \
    LOG_JSON=true \
    PORT=8000 \
    RUN_MIGRATIONS=true \
    AUTO_CREATE_SCHEMA=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# The entrypoint runs `alembic upgrade head` first, then execs uvicorn with a
# single worker: the model is held in memory, so scale out with more instances
# rather than more workers per instance.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
