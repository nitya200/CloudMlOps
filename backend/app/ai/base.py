"""Summarizer abstraction shared by every backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.ai.prompts import SummaryLengthStrategy


@dataclass(frozen=True)
class SummarizationOutput:
    summary_text: str
    chunk_count: int = 1
    model_name: str = "unknown"
    backend: str = "unknown"
    metadata: dict = field(default_factory=dict)


class Summarizer(ABC):
    """Contract the business tier programs against.

    Keeping this interface narrow is what allows the platform to run with
    FLAN-T5 in production and a deterministic stub in CI.
    """

    backend: str = "unknown"

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    def is_ready(self) -> bool:
        return True

    def warmup(self) -> None:  # noqa: B027 - optional hook, not every backend loads weights
        """Optional eager initialization at application startup."""

    @abstractmethod
    def summarize(self, text: str, strategy: SummaryLengthStrategy) -> SummarizationOutput: ...
