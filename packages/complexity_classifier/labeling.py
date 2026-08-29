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

_OPEN_ENDED_STARTERS = (
    "design ",
    "debug ",
    "analyze ",
    "compare ",
    "propose ",
    "plan ",
    "trace ",
    "given ",
    "evaluate ",
    "a user reports",
)

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "by",
        "in",
        "on",
        "at",
        "to",
        "of",
        "for",
        "and",
        "or",
        "that",
        "this",
        "it",
        "its",
        "with",
        "as",
        "from",
        "you",
        "get",
        "when",
        "what",
        "who",
        "how",
        "many",
        "does",
        "do",
        "can",
        "will",
        "has",
        "have",
        "had",
        "been",
        "being",
        "into",
        "through",
        "about",
        "your",
        "their",
        "there",
        "here",
        "also",
        "more",
        "most",
        "some",
        "such",
        "than",
        "then",
        "them",
        "they",
        "these",
        "those",
        "very",
        "just",
        "only",
        "even",
        "like",
        "one",
        "two",
        "three",
    }
)

_ANSWER_PATTERNS = (
    r"you get (.+?)(?:\.|,|;|\n|$)",
    r"written by (.+?)(?:\.|,|;|\n|$)",
    r"is the (.+?)(?:\.|,|;|\n|$)",
    r"there are (\d+(?:\.\d+)?)",
    r"equal to (\d+(?:\.\d+)?)",
    r"is (\d+(?:\.\d+)?) ",
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


def is_short_factual_prompt(prompt: str) -> bool:
    """Short Q&A prompts (not explain/design/debug style)."""
    lowered = prompt.strip().lower()
    if word_count(prompt) > 14:
        return False
    if any(lowered.startswith(s) for s in _OPEN_ENDED_STARTERS):
        return False
    if lowered.startswith("explain ") or lowered.startswith("describe "):
        return False
    factual_patterns = (
        r"^what (is|are|does|color|organ|happens|year|gas)",
        r"^who (wrote|invented|discovered)",
        r"^how many ",
        r"^when (did|was|is)",
        r"^where (is|are)",
        r"^which (is|are)",
        r"^name ",
    )
    return any(re.search(p, lowered) for p in factual_patterns)


def cosine_sim(a: str, b: str, encoder) -> float:
    embeddings = encoder.encode([a, b])
    return float(cosine_similarity([embeddings[0]], [embeddings[1]])[0, 0])


def _split_first_clause(text: str) -> str:
    for sep in (",", ";", "\n"):
        if sep in text:
            return text.split(sep, 1)[0]
    match = re.search(r"(?<![A-Z])\.(?=\s|$)", text)
    if match:
        return text[: match.start()]
    return text


def extract_key_phrase(text: str) -> str:
    """Extract a short answer phrase from model output."""
    lowered = normalize_text(text)
    for prefix in _ANSWER_PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :]
            break

    for pattern in _ANSWER_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            return match.group(1).strip(" .,!?:;\"'")

    return _split_first_clause(lowered).strip(" .,!?:;\"'")


def extract_numbers(text: str) -> list[str]:
    return re.findall(r"\b\d+(?:\.\d+)?\b", text)


def extract_content_tokens(text: str, *, max_tokens: int = 3) -> list[str]:
    tokens = re.findall(r"\b[a-z][a-z'-]{2,}\b", normalize_text(text))
    return [token for token in tokens if token not in _STOPWORDS][:max_tokens]


def answer_token_overlap(small_text: str, large_text: str) -> bool:
    """Check if distinctive content tokens from the shorter answer appear in the longer."""
    small_norm = normalize_text(small_text)
    large_norm = normalize_text(large_text)
    shorter, longer = (
        (small_norm, large_norm) if len(small_norm) <= len(large_norm) else (large_norm, small_norm)
    )
    tokens = extract_content_tokens(shorter, max_tokens=8)
    distinctive = [token for token in tokens if len(token) >= 5]
    if not distinctive:
        distinctive = tokens[:2]
    if not distinctive:
        return False
    return any(token in longer for token in distinctive)


def answer_number_match(small_text: str, large_text: str) -> bool:
    """
    For numeric answers: large model's largest number must appear in small output.

    Avoids false positives when both mention intermediate values (e.g. 60 min/hr)
    but only the large model states the final answer (180).
    """
    large_nums = [float(n) for n in extract_numbers(large_text)]
    if not large_nums:
        return False
    max_large = max(large_nums)
    max_token = str(int(max_large)) if max_large == int(max_large) else str(max_large)
    small_norm = normalize_text(small_text)
    return max_token in small_norm


def substring_answer_match(
    small_text: str,
    large_text: str,
    prompt: str | None = None,
) -> bool:
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

    if prompt and is_short_factual_prompt(prompt):
        if answer_number_match(small_text, large_text):
            return True
    else:
        for num in extract_numbers(large_text):
            if num in small_norm:
                return True

    if answer_token_overlap(small_text, large_text):
        how_many = prompt and prompt.strip().lower().startswith("how many")
        if not how_many:
            return True

    return False


def label_outputs(
    small_text: str,
    large_text: str,
    encoder,
    *,
    prompt: str | None = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    short_output_words: int = DEFAULT_SHORT_OUTPUT_WORDS,
) -> LabelResult:
    """
    Derive small_sufficient from model output pair.

    - Terse outputs or short factual prompts: substring/number agreement overrides low cosine.
    - Longer open-ended outputs: cosine similarity is the primary signal.
    """
    sim = cosine_sim(small_text, large_text, encoder)
    small_short = word_count(small_text) <= short_output_words
    large_short = word_count(large_text) <= short_output_words
    terse_outputs = small_short or large_short
    factual_prompt = prompt is not None and is_short_factual_prompt(prompt)
    check_substring = terse_outputs or factual_prompt
    substring_match = (
        substring_answer_match(small_text, large_text, prompt) if check_substring else False
    )

    if check_substring and substring_match:
        small_sufficient = True
        method = "short_substring_match" if terse_outputs else "factual_substring_match"
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
