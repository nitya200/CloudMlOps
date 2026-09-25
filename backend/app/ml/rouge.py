"""Lightweight ROUGE F1 helpers (no external dependency)."""

from __future__ import annotations

import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _ngrams(tokens: list[str], n: int) -> Counter[tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def _f1(reference: Counter, hypothesis: Counter) -> float:
    if not hypothesis:
        return 0.0
    overlap = sum((reference & hypothesis).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(hypothesis.values())
    recall = overlap / sum(reference.values()) if reference else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def rouge_n(reference: str, hypothesis: str, n: int) -> float:
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    return _f1(_ngrams(ref_tokens, n), _ngrams(hyp_tokens, n))


def rouge_l(reference: str, hypothesis: str) -> float:
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    if not ref_tokens or not hyp_tokens:
        return 0.0
    # Longest common subsequence length → recall/precision F1 on token sequences.
    lengths = [[0] * (len(hyp_tokens) + 1) for _ in range(len(ref_tokens) + 1)]
    for i, ref_tok in enumerate(ref_tokens, start=1):
        for j, hyp_tok in enumerate(hyp_tokens, start=1):
            if ref_tok == hyp_tok:
                lengths[i][j] = lengths[i - 1][j - 1] + 1
            else:
                lengths[i][j] = max(lengths[i - 1][j], lengths[i][j - 1])
    lcs = lengths[-1][-1]
    if lcs == 0:
        return 0.0
    recall = lcs / len(ref_tokens)
    precision = lcs / len(hyp_tokens)
    return 2 * precision * recall / (precision + recall)


def average_rouge(references: list[str], hypotheses: list[str]) -> dict[str, float]:
    if not references or len(references) != len(hypotheses):
        return {"rouge_1": 0.0, "rouge_2": 0.0, "rouge_l": 0.0}
    scores = {"rouge_1": 0.0, "rouge_2": 0.0, "rouge_l": 0.0}
    for ref, hyp in zip(references, hypotheses, strict=True):
        scores["rouge_1"] += rouge_n(ref, hyp, 1)
        scores["rouge_2"] += rouge_n(ref, hyp, 2)
        scores["rouge_l"] += rouge_l(ref, hyp)
    count = len(references)
    return {key: round(value / count, 4) for key, value in scores.items()}
