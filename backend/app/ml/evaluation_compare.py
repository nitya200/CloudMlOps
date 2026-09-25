"""Compare candidate summarizer ROUGE to extractive baseline (proposal evaluation row)."""

from __future__ import annotations

import json

from app.ai.base import Summarizer
from app.ai.extractive import ExtractiveSummarizer
from app.ai.factory import get_summarizer
from app.ml.evaluation import evaluate_summarizer


def evaluate_with_baseline(candidate: Summarizer | None = None) -> dict[str, object]:
    """ROUGE for candidate vs extractive reference (concise / DistilBART-class baseline)."""
    candidate = candidate or get_summarizer()
    baseline = ExtractiveSummarizer()
    candidate_scores = evaluate_summarizer(candidate)
    baseline_scores = evaluate_summarizer(baseline)
    return {
        "candidate_backend": candidate.backend,
        "candidate_model": candidate.model_name,
        "baseline_backend": baseline.backend,
        "baseline_label": "extractive concise reference (proposal DistilBART-class baseline)",
        "candidate_rouge": candidate_scores,
        "baseline_rouge": baseline_scores,
    }


def format_evaluation_notes(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2)
