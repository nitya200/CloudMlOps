"""Summary length strategies.

Strategy pattern: each supported summary length is an object that owns its
prompt template and its generation parameters. The summarizers depend on the
abstract ``SummaryLengthStrategy``, so adding a "bullet points" or "executive
brief" mode never touches the model code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.exceptions import ValidationError
from app.models.enums import SummaryLength


@dataclass(frozen=True)
class GenerationParams:
    """Decoder settings handed to ``model.generate``."""

    max_new_tokens: int
    min_new_tokens: int
    num_beams: int = 4
    length_penalty: float = 1.0
    no_repeat_ngram_size: int = 3


class SummaryLengthStrategy(ABC):
    """Defines how one summary length is prompted and decoded."""

    length: SummaryLength
    label: str
    target_words: int
    chunk_max_words: int = 350

    @property
    @abstractmethod
    def params(self) -> GenerationParams: ...

    @abstractmethod
    def instruction(self) -> str:
        """The natural language instruction prefixed to the input text."""

    def build_prompt(self, text: str) -> str:
        return f"{self.instruction()}\n\n{text}"

    def build_reduce_prompt(self, partial_summaries: str) -> str:
        """Prompt for the reduce step when a document was summarized in chunks."""
        return (
            f"{self.instruction()} Combine the section summaries below into one "
            f"coherent summary without repeating information.\n\n{partial_summaries}"
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} target_words={self.target_words}>"


class ShortSummaryStrategy(SummaryLengthStrategy):
    length = SummaryLength.SHORT
    label = "Short (2-3 sentences)"
    target_words = 55
    chunk_max_words = 350

    @property
    def params(self) -> GenerationParams:
        return GenerationParams(max_new_tokens=90, min_new_tokens=25, length_penalty=0.9)

    def instruction(self) -> str:
        return (
            "Summarize the following document in 2 to 3 sentences. "
            "Capture only the most important idea and outcome."
        )


class MediumSummaryStrategy(SummaryLengthStrategy):
    length = SummaryLength.MEDIUM
    label = "Medium (one paragraph)"
    target_words = 130
    chunk_max_words = 380

    @property
    def params(self) -> GenerationParams:
        return GenerationParams(max_new_tokens=200, min_new_tokens=60, length_penalty=1.0)

    def instruction(self) -> str:
        return (
            "Write a concise one-paragraph summary of the following document. "
            "Cover the main topic, the key supporting points and any conclusion."
        )


class LongSummaryStrategy(SummaryLengthStrategy):
    length = SummaryLength.LONG
    label = "Long (detailed multi-paragraph)"
    target_words = 260
    chunk_max_words = 420

    @property
    def params(self) -> GenerationParams:
        return GenerationParams(max_new_tokens=380, min_new_tokens=140, length_penalty=1.2)

    def instruction(self) -> str:
        return (
            "Write a detailed summary of the following document. "
            "Explain the main topic, the supporting arguments, any data or "
            "findings mentioned, and the conclusion."
        )


class SummaryStrategyFactory:
    """Resolves a ``SummaryLength`` enum value to its strategy object."""

    _registry: dict[SummaryLength, type[SummaryLengthStrategy]] = {
        SummaryLength.SHORT: ShortSummaryStrategy,
        SummaryLength.MEDIUM: MediumSummaryStrategy,
        SummaryLength.LONG: LongSummaryStrategy,
    }

    @classmethod
    def create(cls, length: SummaryLength | str) -> SummaryLengthStrategy:
        try:
            key = SummaryLength(str(length).lower())
        except ValueError as exc:
            valid = ", ".join(item.value for item in SummaryLength)
            raise ValidationError(
                f"Unknown summary length '{length}'. Use one of: {valid}."
            ) from exc
        return cls._registry[key]()

    @classmethod
    def available(cls) -> list[dict[str, object]]:
        return [
            {
                "value": str(length),
                "label": cls._registry[length]().label,
                "target_words": cls._registry[length]().target_words,
            }
            for length in SummaryLength
        ]
