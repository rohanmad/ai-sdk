"""Regex/pattern-based PII rules (v1), combined with optional NER (v2)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from packages.sensitivity_gate.ner_classifier import check_ner_sensitivity


@dataclass(frozen=True)
class SensitivityRule:
    name: str
    pattern: re.Pattern[str]
    description: str


DEFAULT_RULES: tuple[SensitivityRule, ...] = (
    SensitivityRule(
        name="email",
        pattern=re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
        description="Email address detected",
    ),
    SensitivityRule(
        name="phone_us",
        pattern=re.compile(
            r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        description="US phone number detected",
    ),
    SensitivityRule(
        name="ssn",
        pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        description="SSN-shaped pattern detected",
    ),
    SensitivityRule(
        name="credit_card",
        pattern=re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        description="Credit-card-shaped pattern detected",
    ),
)


@dataclass
class SensitivityResult:
    is_sensitive: bool
    triggers: list[str]
    matched_rules: list[str]


def check_sensitivity(
    text: str,
    rules: tuple[SensitivityRule, ...] = DEFAULT_RULES,
    *,
    use_ner: bool = True,
) -> SensitivityResult:
    """Regex + optional NER gate — sensitive if either path flags the prompt."""
    matched: list[str] = []
    for rule in rules:
        if rule.pattern.search(text):
            matched.append(rule.name)

    regex_triggers = [r.description for r in rules if r.name in matched]

    ner_matched: list[str] = []
    ner_triggers: list[str] = []
    if use_ner:
        ner_result = check_ner_sensitivity(text)
        ner_matched = ner_result.matched_rules
        ner_triggers = ner_result.triggers

    return SensitivityResult(
        is_sensitive=bool(matched or ner_matched),
        triggers=regex_triggers + ner_triggers,
        matched_rules=matched + ner_matched,
    )
