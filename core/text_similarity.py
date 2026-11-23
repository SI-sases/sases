"""Small, dependency-free text similarity helpers.

This replaces sklearn TF-IDF for the client runtime.  It is intentionally
simple: character n-gram cosine similarity is enough for duplicate detection
and avoids shipping scipy/sklearn (~120 MB).
"""
from __future__ import annotations

import re
from collections import Counter

_WS = re.compile(r"\s+")


def _grams(text: str) -> Counter:
    text = _WS.sub("", text.lower())
    grams = Counter()
    for n in (2, 3):
        for index in range(max(0, len(text) - n + 1)):
            grams[text[index:index + n]] += 1
    if not grams:
        grams[text] = 1
    return grams


def cosine(left: str, right: str) -> float:
    a, b = _grams(left), _grams(right)
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    norm_a = sum(value * value for value in a.values()) ** 0.5
    norm_b = sum(value * value for value in b.values()) ** 0.5
    if not norm_a or not norm_b:
        return 0.0
    return float(dot / (norm_a * norm_b))


def best_similarity(target: str, candidates: list[str]) -> float:
    return max((cosine(target, item) for item in candidates), default=0.0)


def similarities(target: str, candidates: list[str]) -> list[float]:
    return [cosine(target, item) for item in candidates]
