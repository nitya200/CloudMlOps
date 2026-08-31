"""Lazy, thread-safe, process-wide loader for the FLAN-T5 checkpoint.

Loading a transformer costs seconds and hundreds of megabytes of RAM, so the
model is loaded at most once per process and shared by every request. FastAPI
serves requests from a thread pool, hence the lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any

from app.core.config import settings
from app.core.exceptions import SummarizationError
from app.core.logging import get_logger

logger = get_logger(__name__)


def transformers_available() -> bool:
    """True when both transformers and torch can be imported."""
    return find_spec("transformers") is not None and find_spec("torch") is not None


@dataclass
class LoadedModel:
    tokenizer: Any
    model: Any
    model_name: str
    device: str
    max_input_tokens: int


class ModelLoader:
    """Singleton holder for the sequence-to-sequence model."""

    _instance: ModelLoader | None = None
    _class_lock = threading.Lock()

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.ai_model_name
        self._loaded: LoadedModel | None = None
        self._lock = threading.Lock()

    @classmethod
    def instance(cls) -> ModelLoader:
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Drop the cached instance. Used by tests."""
        with cls._class_lock:
            cls._instance = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._loaded is not None

    def load(self) -> LoadedModel:
        if self._loaded is not None:
            return self._loaded
        with self._lock:
            if self._loaded is not None:  # another thread won the race
                return self._loaded
            self._loaded = self._do_load()
        return self._loaded

    def _do_load(self) -> LoadedModel:
        if not transformers_available():
            raise SummarizationError(
                "transformers/torch are not installed. Install "
                "requirements-ai.txt or set AI_BACKEND=extractive."
            )
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        cache_dir = str(settings.ai_model_cache_dir) if settings.ai_model_cache_dir else None
        logger.info("loading summarization model", extra={"model": self._model_name})

        tokenizer = AutoTokenizer.from_pretrained(self._model_name, cache_dir=cache_dir)
        model = AutoModelForSeq2SeqLM.from_pretrained(self._model_name, cache_dir=cache_dir)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
        # Inference only: gradients would waste memory on every request.
        for parameter in model.parameters():
            parameter.requires_grad_(False)

        max_input_tokens = int(getattr(tokenizer, "model_max_length", 512) or 512)
        if max_input_tokens > 4096:  # some tokenizers report a sentinel value
            max_input_tokens = 512

        logger.info(
            "summarization model ready",
            extra={"model": self._model_name, "device": device, "max_input": max_input_tokens},
        )
        return LoadedModel(
            tokenizer=tokenizer,
            model=model,
            model_name=self._model_name,
            device=device,
            max_input_tokens=max_input_tokens,
        )
