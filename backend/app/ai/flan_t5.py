"""FLAN-T5 abstractive summarizer with map-reduce over long documents."""

from __future__ import annotations

import threading

from app.ai.base import SummarizationOutput, Summarizer
from app.ai.model_loader import ModelLoader
from app.ai.prompts import SummaryLengthStrategy
from app.core.config import settings
from app.core.exceptions import SummarizationError
from app.core.logging import get_logger
from app.utils.text_utils import chunk_text, normalize_text, word_count

logger = get_logger(__name__)

# Generation is CPU bound and not thread safe for a shared module, so requests
# are serialized. On App Runner, concurrency is handled by running more
# instances rather than more threads per model.
_generation_lock = threading.Lock()

MAX_REDUCE_ROUNDS = 3


class FlanT5Summarizer(Summarizer):
    backend = "flan-t5"

    def __init__(self, loader: ModelLoader | None = None) -> None:
        self._loader = loader or ModelLoader.instance()

    @property
    def model_name(self) -> str:
        return self._loader.model_name

    @property
    def is_ready(self) -> bool:
        return self._loader.is_loaded

    def warmup(self) -> None:
        self._loader.load()

    def summarize(self, text: str, strategy: SummaryLengthStrategy) -> SummarizationOutput:
        cleaned = normalize_text(text)
        if not cleaned:
            raise SummarizationError("There is no text to summarize.")
        if len(cleaned) > settings.ai_max_input_chars:
            # Hard cap protects the container from a pathological upload.
            cleaned = cleaned[: settings.ai_max_input_chars]
            logger.warning("input truncated to the configured character limit")

        chunks = chunk_text(cleaned, max_words=strategy.chunk_max_words, overlap_words=15)
        if not chunks:
            raise SummarizationError("There is no text to summarize.")

        # Map: summarize each chunk that fits the 512-token encoder window.
        partials = [self._generate(strategy.build_prompt(chunk), strategy) for chunk in chunks]
        total_chunks = len(chunks)

        # Reduce: fold the partial summaries until a single summary remains.
        rounds = 0
        while len(partials) > 1 and rounds < MAX_REDUCE_ROUNDS:
            joined = "\n".join(f"- {part}" for part in partials)
            groups = chunk_text(joined, max_words=strategy.chunk_max_words, overlap_words=0)
            partials = [
                self._generate(strategy.build_reduce_prompt(group), strategy) for group in groups
            ]
            rounds += 1

        summary = " ".join(partials).strip() if len(partials) > 1 else partials[0].strip()
        if not summary:
            raise SummarizationError("The model returned an empty summary. Please try again.")

        return SummarizationOutput(
            summary_text=summary,
            chunk_count=total_chunks,
            model_name=self.model_name,
            backend=self.backend,
            metadata={
                "reduce_rounds": rounds,
                "input_words": word_count(cleaned),
                "strategy": str(strategy.length),
            },
        )

    def _generate(self, prompt: str, strategy: SummaryLengthStrategy) -> str:
        loaded = self._loader.load()
        params = strategy.params
        try:
            import torch

            inputs = loaded.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=loaded.max_input_tokens,
            ).to(loaded.device)

            with _generation_lock, torch.inference_mode():
                output_ids = loaded.model.generate(
                    **inputs,
                    max_new_tokens=params.max_new_tokens,
                    min_new_tokens=params.min_new_tokens,
                    num_beams=params.num_beams,
                    length_penalty=params.length_penalty,
                    no_repeat_ngram_size=params.no_repeat_ngram_size,
                    early_stopping=True,
                )
            decoded = loaded.tokenizer.decode(output_ids[0], skip_special_tokens=True)
            return decoded.strip()
        except SummarizationError:
            raise
        except Exception as exc:
            logger.exception("model generation failed")
            raise SummarizationError(
                "The summarization model failed to process this text. Please try again."
            ) from exc
