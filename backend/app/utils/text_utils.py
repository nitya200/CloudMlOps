"""Text normalization and chunking shared by extraction and summarization."""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"[ \t\x0b\f\r]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def normalize_text(raw: str) -> str:
    """Collapse the whitespace noise typical of PDF text layers."""
    if not raw:
        return ""
    text = raw.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)  # re-join words split across lines
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def preview(text: str, limit: int = 240) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "\u2026"


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts: list[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue
        parts.extend(part.strip() for part in _SENTENCE_SPLIT.split(block) if part.strip())
    return parts


def chunk_text(text: str, *, max_words: int, overlap_words: int = 0) -> list[str]:
    """Split text into sentence-aligned chunks of at most ``max_words`` words.

    FLAN-T5 has a 512 token encoder window, so long documents must be
    summarized in pieces and then combined. Splitting on sentence boundaries
    keeps each chunk readable instead of cutting mid-clause.
    """
    if max_words <= 0:
        raise ValueError("max_words must be positive")
    sentences = split_sentences(text) or ([text] if text.strip() else [])
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        words = sentence.split()
        if not words:
            continue
        # A single oversized sentence is hard-split rather than dropped.
        if len(words) > max_words:
            if current:
                chunks.append(" ".join(current))
                current, current_words = [], 0
            for start in range(0, len(words), max_words):
                chunks.append(" ".join(words[start : start + max_words]))
            continue
        if current_words + len(words) > max_words:
            chunks.append(" ".join(current))
            tail = current[-overlap_words:] if overlap_words else []
            current = [*tail, sentence]
            current_words = sum(len(part.split()) for part in current)
        else:
            current.append(sentence)
            current_words += len(words)

    if current:
        chunks.append(" ".join(current))
    return [chunk for chunk in chunks if chunk.strip()]
