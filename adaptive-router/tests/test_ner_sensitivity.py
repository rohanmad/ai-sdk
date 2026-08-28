"""Tests for spaCy NER sensitivity detection."""

from __future__ import annotations

import pytest

spacy = pytest.importorskip("spacy")

from packages.sensitivity_gate.ner_classifier import (  # noqa: E402
    SENSITIVE_ENTITY_LABELS,
    check_ner_sensitivity,
    ner_available,
)
from packages.sensitivity_gate.rules import check_sensitivity  # noqa: E402

pytestmark = pytest.mark.skipif(
    not ner_available(),
    reason="en_core_web_sm not installed (python -m spacy download en_core_web_sm)",
)


def test_ner_flags_person_name() -> None:
    result = check_sensitivity(
        "Please send the report to Sarah Johnson by end of day.",
        use_ner=True,
    )
    assert result.is_sensitive is True
    assert any(rule.startswith("ner:PERSON") for rule in result.matched_rules)
    assert any("PERSON" in trigger for trigger in result.triggers)


def test_ner_flags_location() -> None:
    result = check_sensitivity(
        "Ship the package to Boston, Massachusetts tomorrow.",
        use_ner=True,
    )
    assert result.is_sensitive is True
    assert any(
        rule.startswith("ner:GPE") or rule.startswith("ner:LOC")
        for rule in result.matched_rules
    )


def test_ner_flags_organization() -> None:
    result = check_sensitivity(
        "I work at Acme Corporation on a confidential project.",
        use_ner=True,
    )
    assert result.is_sensitive is True
    assert any(rule.startswith("ner:ORG") for rule in result.matched_rules)


def test_ner_ignores_benign_prompt() -> None:
    result = check_sensitivity(
        "Explain how photosynthesis converts light into chemical energy.",
        use_ner=True,
    )
    assert result.is_sensitive is False
    assert result.matched_rules == []


def test_ner_false_positive_prone_common_word() -> None:
    """Documents model behavior on ambiguous tokens (e.g. Will as a name)."""
    result = check_ner_sensitivity("Will the deployment finish on time?")
    # Record behavior without asserting a specific outcome — spaCy version dependent.
    assert isinstance(result.is_sensitive, bool)
    assert isinstance(result.matched_rules, list)


def test_combined_regex_and_ner_triggers() -> None:
    result = check_sensitivity(
        "Email alice@example.com about meeting Sarah Johnson in Boston.",
        use_ner=True,
    )
    assert result.is_sensitive is True
    assert "email" in result.matched_rules
    assert any(rule.startswith("ner:") for rule in result.matched_rules)
    assert len(result.triggers) >= 2


def test_regex_only_when_ner_disabled() -> None:
    result = check_sensitivity(
        "Please send the report to Sarah Johnson by end of day.",
        use_ner=False,
    )
    assert result.is_sensitive is False


def test_sensitive_entity_labels_exclude_dates_and_money() -> None:
    assert "DATE" not in SENSITIVE_ENTITY_LABELS
    assert "TIME" not in SENSITIVE_ENTITY_LABELS
    assert "MONEY" not in SENSITIVE_ENTITY_LABELS
    assert "CARDINAL" not in SENSITIVE_ENTITY_LABELS
