"""Dependency-free extractive summarizer.

Used as the fallback when transformers/torch are unavailable (CI, low-memory
machines, cold-start protection). It scores sentences by normalized term
frequency and returns the highest scoring ones in their original order, so the
platform always produces a usable summary instead of a 503.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.ai.base import SummarizationOutput, Summarizer
from app.ai.prompts import SummaryLengthStrategy
from app.core.exceptions import SummarizationError
from app.utils.text_utils import normalize_text, split_sentences, word_count

_WORD = re.compile(r"[A-Za-z0-9']+")

_STOPWORD_LIST = (
    "a about above after again against all also am an and any are aren't as at "
    "be because been before being below between both but by "
    "can cannot could couldn't did didn't do does doesn't doing don't down during "
    "each few for from further had hadn't has hasn't have haven't having "
    "he her here hers herself him himself his how "
    "i if in into is isn't it its itself let's may me might more most mustn't my myself "
    "no nor not of off on once only or other ought our ours ourselves out over own "
    "same shan't she should shouldn't so some such "
    "than that the their theirs them themselves then there these they this those "
    "through to too under until up upon very "
    "was wasn't we were weren't what when where which while who whom why with within "
    "won't would wouldn't you your yours yourself yourselves"
)

STOPWORDS = frozenset(_STOPWORD_LIST.split())


class ExtractiveSummarizer(Summarizer):
    backend = "extractive"

    @property
    def model_name(self) -> str:
        return "tf-weighted-extractive"

    def summarize(self, text: str, strategy: SummaryLengthStrategy) -> SummarizationOutput:
        cleaned = normalize_text(text)
        sentences = split_sentences(cleaned)
        if not sentences:
            raise SummarizationError("There is no text to summarize.")

        frequencies = self._term_frequencies(cleaned)
        scored = [
            (index, self._score(sentence, frequencies, index, len(sentences)))
            for index, sentence in enumerate(sentences)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)

        selected: list[int] = []
        words_used = 0
        for index, _score in scored:
            selected.append(index)
            words_used += word_count(sentences[index])
            if words_used >= strategy.target_words:
                break

        selected.sort()  # restore reading order
        summary = " ".join(sentences[index] for index in selected).strip()
        return SummarizationOutput(
            summary_text=summary,
            chunk_count=1,
            model_name=self.model_name,
            backend=self.backend,
            metadata={
                "sentences_selected": len(selected),
                "sentences_total": len(sentences),
                "strategy": str(strategy.length),
            },
        )

    @staticmethod
    def _term_frequencies(text: str) -> dict[str, float]:
        tokens = [
            token.lower()
            for token in _WORD.findall(text)
            if token.lower() not in STOPWORDS and len(token) > 2
        ]
        if not tokens:
            return {}
        counts = Counter(tokens)
        peak = max(counts.values())
        return {term: count / peak for term, count in counts.items()}

    @staticmethod
    def _score(sentence: str, frequencies: dict[str, float], index: int, total: int) -> float:
        tokens = [token.lower() for token in _WORD.findall(sentence)]
        content = [token for token in tokens if token not in STOPWORDS and len(token) > 2]
        if not content:
            return 0.0
        # Mean term weight, dampened for very short sentences so single-clause
        # fragments do not outrank substantive ones.
        base = sum(frequencies.get(token, 0.0) for token in content) / math.sqrt(len(content))
        # Documents put their thesis near the top; give early sentences a nudge.
        position_bonus = 1.15 if index < max(1, total // 10) else 1.0
        return base * position_bonus
