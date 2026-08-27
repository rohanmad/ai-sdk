"""Feature extraction for complexity classification (step 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass

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
