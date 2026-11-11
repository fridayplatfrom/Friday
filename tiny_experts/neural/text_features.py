"""Versioned, deterministic text features for small supervised classifiers.

This representation is deliberately modest: normalized word and bigram counts.
It is not a language model, and preserving negation tokens does not by itself
make the classifier understand negation.
"""

from collections import Counter
import hashlib
import json
import math
import re
from typing import Iterable


FEATURE_VERSION = "unicode_word_bigram_l2_v1"
_WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)


def tokenize(text: str) -> list[str]:
    words = _WORD.findall(text.casefold().replace("’", "'"))
    return words + [f"{left}_{right}" for left, right in zip(words, words[1:])]


def build_vocabulary(texts: Iterable[str], max_features: int = 1000) -> dict[str, int]:
    if max_features < 1:
        raise ValueError("max_features must be positive")
    counts = Counter(token for text in texts for token in tokenize(text))
    # Stable tie breaking makes vocabulary hashes reproducible.
    ranked = sorted(counts, key=lambda token: (-counts[token], token))
    return {token: index for index, token in enumerate(ranked[:max_features])}


def validate_vocabulary(vocabulary: dict, feature_dim: int) -> None:
    if not isinstance(vocabulary, dict) or not vocabulary:
        raise ValueError("Vocabulary must be a nonempty object")
    if not all(isinstance(k, str) and k for k in vocabulary):
        raise ValueError("Vocabulary tokens must be nonempty strings")
    if not all(type(v) is int for v in vocabulary.values()):
        raise ValueError("Vocabulary indices must be integers")
    if len(vocabulary) != feature_dim or set(vocabulary.values()) != set(range(feature_dim)):
        raise ValueError("Vocabulary indices must match the model feature dimension")


def vectorize(text: str, vocabulary: dict[str, int]) -> list[float]:
    values = [0.0] * len(vocabulary)
    for token in tokenize(text):
        index = vocabulary.get(token)
        if index is not None:
            values[index] += 1.0
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values] if norm else values


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
