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


_NAME_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "trying",
        "building",
        "wondering",
        "asking",
        "going",
        "not",
        "just",
        "also",
        "very",
        "really",
        "having",
        "getting",
        "using",
        "writing",
        "looking",
        "working",
        "hoping",
        "thinking",
        "new",
        "here",
        "sure",
        "sorry",
        "glad",
        "happy",
        "currently",
        "still",
        "actually",
    }
)

_MY_NAME_IS = re.compile(
    r"(?i)\bmy name is\s+([a-z][a-z'-]+(?:\s+[a-z][a-z'-]+){0,3})\b"
)
_CALL_ME = re.compile(
    r"(?i)\bcall me\s+([a-z][a-z'-]+(?:\s+[a-z][a-z'-]+){0,3})\b"
)

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
        name="phone_loose",
        pattern=re.compile(
            r"(?i)\b(?:phone|mobile|cell)(?:\s+number)?\s+is\s+\d{7,15}\b"
        ),
        description="Phone number phrase detected",
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


def _match_name_intro(text: str) -> bool:
    """Flag explicit self-introductions, not everyday 'I am …' phrasing."""
    for pattern in (_MY_NAME_IS, _CALL_ME):
        match = pattern.search(text)
        if not match:
            continue
        first_word = match.group(1).strip().lower().split()[0]
        if first_word in _NAME_STOPWORDS:
            continue
        return True
    return False


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

    if _match_name_intro(text):
        matched.append("name_intro")

    regex_triggers = [r.description for r in rules if r.name in matched]
    if "name_intro" in matched:
        regex_triggers.append("Self-identified name detected")

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


def _user_message_contents(
    messages: list[dict[str, str]] | None,
    *,
    fallback: str = "",
) -> list[str]:
    if messages:
        contents = [
            m["content"]
            for m in messages
            if m.get("role") == "user" and m.get("content")
        ]
        if contents:
            return contents
    if fallback:
        return [fallback]
    return []


def check_conversation_sensitivity(
    messages: list[dict[str, str]] | None = None,
    *,
    prompt: str = "",
    use_ner: bool = True,
) -> SensitivityResult:
    """Sensitive if any user turn in the conversation triggers the gate."""
    matched_rules: list[str] = []
    triggers: list[str] = []
    for text in _user_message_contents(messages, fallback=prompt):
        result = check_sensitivity(text, use_ner=use_ner)
        if not result.is_sensitive:
            continue
        for rule in result.matched_rules:
            if rule not in matched_rules:
                matched_rules.append(rule)
        for trigger in result.triggers:
            if trigger not in triggers:
                triggers.append(trigger)
    return SensitivityResult(
        is_sensitive=bool(matched_rules),
        triggers=triggers,
        matched_rules=matched_rules,
    )


def check_latest_user_sensitivity(
    messages: list[dict[str, str]] | None = None,
    *,
    prompt: str = "",
    use_ner: bool = True,
) -> SensitivityResult:
    """Sensitive only if the latest user message triggers the gate."""
    contents = _user_message_contents(messages, fallback=prompt)
    if not contents:
        return SensitivityResult(is_sensitive=False, triggers=[], matched_rules=[])
    return check_sensitivity(contents[-1], use_ner=use_ner)
