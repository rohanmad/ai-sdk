"""Feature extraction for complexity classification (step 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

REASONING_KEYWORDS = frozenset(
    {
        "analyze",
        "compare",
        "debug",
        "design",
        "evaluate",
        "explain",
        "implement",
        "optimize",
        "prove",
        "reason",
        "refactor",
        "solve",
        "trace",
        "why",
    }
)

ENCODER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@dataclass
class ComplexityFeatures:
    char_length: int
    word_count: int
    question_marks: int
    reasoning_keyword_hits: int
    code_block_present: bool
    multi_step_hint: bool


def extract_features(text: str) -> ComplexityFeatures:
    lowered = text.lower()
    words = re.findall(r"\b\w+\b", lowered)
    keyword_hits = sum(1 for w in words if w in REASONING_KEYWORDS)
    return ComplexityFeatures(
        char_length=len(text),
        word_count=len(words),
        question_marks=text.count("?"),
        reasoning_keyword_hits=keyword_hits,
        code_block_present="```" in text,
        multi_step_hint=any(
            marker in lowered
            for marker in ("step 1", "first,", "then ", "finally ", "1.", "2.")
        ),
    )


@lru_cache(maxsize=1)
def _get_encoder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(ENCODER_NAME)


def embed_prompt(text: str) -> np.ndarray:
    """Return 384-dim sentence-transformer embedding for prompt text."""
    encoder = _get_encoder()
    vector = encoder.encode(text, show_progress_bar=False)
    return np.asarray(vector, dtype=np.float64)


def embed_prompts(texts: list[str]) -> np.ndarray:
    """Batch-embed prompts; returns shape (n, 384)."""
    if not texts:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float64)
    encoder = _get_encoder()
    vectors = encoder.encode(texts, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float64)
