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

OPEN_ENDED_STARTERS = (
    "design ",
    "debug ",
    "analyze ",
    "compare ",
    "propose ",
    "plan ",
    "trace ",
    "evaluate ",
    "given ",
)

IMPERATIVE_MULTI_STEP_MARKERS = (
    "step-by-step",
    "step by step",
    "outline ",
    "list a ",
    "list the ",
    "list three",
    "list five",
)

FACTUAL_PATTERNS = (
    r"^what is\b",
    r"^what are\b",
    r"^what does\b",
    r"^what year\b",
    r"^what color\b",
    r"^what gas\b",
    r"^what organ\b",
    r"^who wrote\b",
    r"^who invented\b",
    r"^who discovered\b",
    r"^who developed\b",
    r"^who painted\b",
    r"^how many\b",
    r"^when did\b",
    r"^when was\b",
    r"^where is\b",
    r"^where are\b",
    r"^which is\b",
    r"^which are\b",
    r"^name the\b",
    r"^what is the (capital|chemical|atomic|largest|smallest|main|primary|fastest|deepest|softest)\b",
    r"^what is \d+",
    r"^how many (days|hours|minutes|seconds|weeks|months|planets|states|bones|teeth|legs|players|sides|degrees|bytes|bits|continents)\b",
)

ENCODER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

WORD_COUNT_SHORT_MAX = 8
WORD_COUNT_MEDIUM_MAX = 15


@dataclass
class ComplexityFeatures:
    char_length: int
    word_count: int
    question_marks: int
    reasoning_keyword_hits: int
    code_block_present: bool
    multi_step_hint: bool
    open_ended_starter: bool
    imperative_multi_step: bool
    factual_pattern: bool
    length_bucket_short: bool
    length_bucket_medium: bool
    length_bucket_long: bool


def _word_count(lowered: str) -> int:
    return len(re.findall(r"\b\w+\b", lowered))


def _length_buckets(word_count: int) -> tuple[bool, bool, bool]:
    short = word_count <= WORD_COUNT_SHORT_MAX
    medium = WORD_COUNT_SHORT_MAX < word_count <= WORD_COUNT_MEDIUM_MAX
    long = word_count > WORD_COUNT_MEDIUM_MAX
    return short, medium, long


def extract_features(text: str) -> ComplexityFeatures:
    lowered = text.strip().lower()
    words = re.findall(r"\b\w+\b", lowered)
    word_count = len(words)
    keyword_hits = sum(1 for w in words if w in REASONING_KEYWORDS)
    short, medium, long = _length_buckets(word_count)
    return ComplexityFeatures(
        char_length=len(text),
        word_count=word_count,
        question_marks=text.count("?"),
        reasoning_keyword_hits=keyword_hits,
        code_block_present="```" in text,
        multi_step_hint=any(
            marker in lowered
            for marker in ("step 1", "first,", "then ", "finally ", "1.", "2.")
        ),
        open_ended_starter=any(lowered.startswith(s) for s in OPEN_ENDED_STARTERS),
        imperative_multi_step=any(m in lowered for m in IMPERATIVE_MULTI_STEP_MARKERS),
        factual_pattern=any(re.search(p, lowered) for p in FACTUAL_PATTERNS),
        length_bucket_short=short,
        length_bucket_medium=medium,
        length_bucket_long=long,
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
