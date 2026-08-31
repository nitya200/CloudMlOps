"""AI tier: model loading, prompt strategies and summarizer backends."""

from app.ai.base import SummarizationOutput, Summarizer
from app.ai.extractive import ExtractiveSummarizer
from app.ai.factory import create_summarizer, get_summarizer, resolve_backend, set_summarizer
from app.ai.flan_t5 import FlanT5Summarizer
from app.ai.model_loader import ModelLoader, transformers_available
from app.ai.prompts import (
    GenerationParams,
    LongSummaryStrategy,
    MediumSummaryStrategy,
    ShortSummaryStrategy,
    SummaryLengthStrategy,
    SummaryStrategyFactory,
)

__all__ = [
    "ExtractiveSummarizer",
    "FlanT5Summarizer",
    "GenerationParams",
    "LongSummaryStrategy",
    "MediumSummaryStrategy",
    "ModelLoader",
    "ShortSummaryStrategy",
    "SummarizationOutput",
    "Summarizer",
    "SummaryLengthStrategy",
    "SummaryStrategyFactory",
    "create_summarizer",
    "get_summarizer",
    "resolve_backend",
    "set_summarizer",
    "transformers_available",
]
