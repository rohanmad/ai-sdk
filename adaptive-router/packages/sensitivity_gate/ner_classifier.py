"""spaCy NER-based sensitive entity detection (additive to regex rules)."""

from __future__ import annotations

from dataclasses import dataclass

# Entity types treated as potentially identifying / sensitive.
SENSITIVE_ENTITY_LABELS: frozenset[str] = frozenset(
    {"PERSON", "GPE", "LOC", "ORG", "NORP"}
)

_NLP = None
_NLP_UNAVAILABLE_REASON: str | None = None


def _load_nlp():
    """Load en_core_web_sm once at import time."""
    global _NLP, _NLP_UNAVAILABLE_REASON
    if _NLP is not None or _NLP_UNAVAILABLE_REASON is not None:
        return _NLP

    try:
        import spacy
    except ImportError as exc:
        _NLP_UNAVAILABLE_REASON = (
            "spacy is not installed (pip install -e '.[ner]')"
        )
        return None

    try:
        _NLP = spacy.load("en_core_web_sm")
    except OSError as exc:
        _NLP_UNAVAILABLE_REASON = (
            "en_core_web_sm is not installed "
            "(python -m spacy download en_core_web_sm)"
        )
        return None

    return _NLP


# Eager load at module init so per-request calls do not pay model load cost.
_load_nlp()


@dataclass
class NerSensitivityResult:
    is_sensitive: bool
    triggers: list[str]
    matched_rules: list[str]
    entities: list[str]


def ner_available() -> bool:
    return _NLP is not None


def ner_unavailable_reason() -> str | None:
    return _NLP_UNAVAILABLE_REASON


def _is_plausible_entity(text: str) -> bool:
    """Drop spaCy noise (single-char repeats, non-alpha tokens)."""
    stripped = text.strip()
    if len(stripped) < 2:
        return False
    if not any(c.isalpha() for c in stripped):
        return False
    if len(set(stripped.lower())) == 1:
        return False
    return True


def check_ner_sensitivity(text: str) -> NerSensitivityResult:
    """Flag prompts containing PERSON, GPE, LOC, ORG, or NORP entities."""
    nlp = _NLP
    if nlp is None:
        return NerSensitivityResult(
            is_sensitive=False,
            triggers=[],
            matched_rules=[],
            entities=[],
        )

    doc = nlp(text)
    seen: set[tuple[str, str]] = set()
    triggers: list[str] = []
    matched_rules: list[str] = []
    entities: list[str] = []

    for ent in doc.ents:
        if ent.label_ not in SENSITIVE_ENTITY_LABELS:
            continue
        if not _is_plausible_entity(ent.text):
            continue
        key = (ent.label_, ent.text)
        if key in seen:
            continue
        seen.add(key)
        rule_name = f"ner:{ent.label_}"
        if rule_name not in matched_rules:
            matched_rules.append(rule_name)
        triggers.append(f"NER {ent.label_} detected: {ent.text}")
        entities.append(f"{ent.label_}:{ent.text}")

    return NerSensitivityResult(
        is_sensitive=bool(matched_rules),
        triggers=triggers,
        matched_rules=matched_rules,
        entities=entities,
    )
