"""Run ROUGE evaluation for a summarizer backend."""

from __future__ import annotations

from app.ai.base import Summarizer
from app.ai.prompts import SummaryStrategyFactory
from app.ml.evaluation_corpus import EVALUATION_SAMPLES
from app.ml.rouge import average_rouge
from app.models.enums import SummaryLength


def evaluate_summarizer(summarizer: Summarizer) -> dict[str, float]:
    references: list[str] = []
    hypotheses: list[str] = []
    strategy = SummaryStrategyFactory.create(SummaryLength.MEDIUM)
    for sample in EVALUATION_SAMPLES:
        output = summarizer.summarize(sample.source_text, strategy)
        references.append(sample.reference_summary)
        hypotheses.append(output.summary_text)
    return average_rouge(references, hypotheses)
