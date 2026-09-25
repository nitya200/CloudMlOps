"""ROUGE metric helpers."""

from app.ml.rouge import average_rouge, rouge_l, rouge_n


def test_rouge_perfect_match() -> None:
    text = "the cat sat on the mat"
    assert rouge_n(text, text, 1) == 1.0
    assert rouge_l(text, text) == 1.0


def test_average_rouge() -> None:
    scores = average_rouge(["a b c", "x y"], ["a b", "x y z"])
    assert 0.0 <= scores["rouge_1"] <= 1.0
    assert scores["rouge_l"] >= 0.0
