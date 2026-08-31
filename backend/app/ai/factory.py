"""Summarizer factory.

Resolves the configured ``AI_BACKEND`` to a concrete summarizer and caches it
for the process lifetime, so the expensive FLAN-T5 weights are held once.
"""

from __future__ import annotations

import threading

from app.ai.base import Summarizer
from app.ai.extractive import ExtractiveSummarizer
from app.ai.flan_t5 import FlanT5Summarizer
from app.ai.model_loader import transformers_available
from app.core.config import AIBackend, settings
from app.core.exceptions import SummarizationError
from app.core.logging import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_cached: Summarizer | None = None


def resolve_backend(requested: AIBackend | None = None) -> str:
    """Decide which backend to use.

    ``auto`` prefers FLAN-T5 and silently degrades to the extractive summarizer
    when the AI wheels are not installed - that keeps CI fast without a
    separate code path.
    """
    choice = requested or settings.ai_backend
    if choice == "extractive":
        return "extractive"
    if choice == "flan-t5":
        if not transformers_available():
            raise SummarizationError(
                "AI_BACKEND=flan-t5 requires transformers and torch "
                "(pip install -r requirements-ai.txt)."
            )
        return "flan-t5"
    return "flan-t5" if transformers_available() else "extractive"


def create_summarizer(requested: AIBackend | None = None) -> Summarizer:
    backend = resolve_backend(requested)
    return FlanT5Summarizer() if backend == "flan-t5" else ExtractiveSummarizer()


def get_summarizer() -> Summarizer:
    global _cached
    if _cached is None:
        with _lock:
            if _cached is None:
                _cached = create_summarizer()
                logger.info(
                    "summarizer selected",
                    extra={"backend": _cached.backend, "model": _cached.model_name},
                )
    return _cached


def set_summarizer(summarizer: Summarizer | None) -> None:
    """Override the cached summarizer. Used by tests and by startup warmup."""
    global _cached
    with _lock:
        _cached = summarizer
