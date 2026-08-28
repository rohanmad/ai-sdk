"""Labeling logic: compare small vs large model outputs for small_sufficient."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.metrics.pairwise import cosine_similarity

ENCODER_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_SHORT_OUTPUT_WORDS = 15

_ANSWER_PREFIXES = (
    "the answer is ",
    "it is ",
    "it's ",
    "there are ",
    "there is ",
    "that would be ",
    "this is ",
)


@dataclass
class LabelResult:
    small_sufficient: bool
    complexity_label: str
    cosine_sim: float
    method: str
    short_output: bool
    substring_match: bool


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def cosine_sim(a: str, b: str, encoder) -> float:
    embeddings = encoder.encode([a, b])
    return float(cosine_similarity([embeddings[0]], [embeddings[1]])[0, 0])


def extract_key_phrase(text: str) -> str:
    """Extract a short answer phrase from model output."""
    lowered = normalize_text(text)
    for prefix in _ANSWER_PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :]
            break
    # Prefer clause breaks that usually follow the core answer.
    for sep in (",", ";", "\n", "."):
        if sep in lowered:
            lowered = lowered.split(sep)[0]
            break
    return lowered.strip(" .,!?:;\"'")


def extract_numbers(text: str) -> list[str]:
    return re.findall(r"\b\d+(?:\.\d+)?\b", text)


def substring_answer_match(small_text: str, large_text: str) -> bool:
    """
    Check if the small output contains the large model's key answer.

    Handles cases like small='12' vs large='The answer is 12, since sqrt(144)=12'.
    """
    small_norm = normalize_text(small_text)
    key = extract_key_phrase(large_text)
    if len(key) >= 2 and key in small_norm:
        return True

    large_norm = normalize_text(large_text)
    if len(large_norm) >= 2 and large_norm in small_norm:
        return True
    if len(small_norm) >= 2 and small_norm in large_norm:
        return True

    for num in extract_numbers(large_text):
        if num in small_norm:
            return True

    return False


def label_outputs(
    small_text: str,
    large_text: str,
    encoder,
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    short_output_words: int = DEFAULT_SHORT_OUTPUT_WORDS,
) -> LabelResult:
    """
    Derive small_sufficient from model output pair.

    - Short large-model outputs: substring/number agreement overrides low cosine.
    - Longer outputs: cosine similarity is the primary signal.
    """
    sim = cosine_sim(small_text, large_text, encoder)
    small_short = word_count(small_text) <= short_output_words
    large_short = word_count(large_text) <= short_output_words
    terse_outputs = small_short or large_short
    substring_match = (
        substring_answer_match(small_text, large_text) if terse_outputs else False
    )

    if terse_outputs and substring_match:
        small_sufficient = True
        method = "short_substring_match"
    elif terse_outputs:
        small_sufficient = sim >= similarity_threshold
        method = "short_cosine"
    else:
        small_sufficient = sim >= similarity_threshold
        method = "long_cosine"

    complexity_label = "low" if small_sufficient else "high"
    return LabelResult(
        small_sufficient=small_sufficient,
        complexity_label=complexity_label,
        cosine_sim=sim,
        method=method,
        short_output=terse_outputs,
        substring_match=substring_match,
    )


def format_notes(result: LabelResult) -> str:
    return (
        f"cosine_sim={result.cosine_sim:.4f}; method={result.method}; "
        f"short_output={str(result.short_output).lower()}; "
        f"substring_match={str(result.substring_match).lower()}"
    )
