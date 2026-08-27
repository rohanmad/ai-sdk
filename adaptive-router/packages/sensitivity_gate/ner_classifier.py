"""NER-based sensitive entity detection (v2 placeholder)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NerSensitivityResult:
    is_sensitive: bool
    entities: list[str]


def check_ner_sensitivity(text: str) -> NerSensitivityResult:
    """Placeholder for spaCy / distilled-transformer NER (not implemented in v1)."""
    _ = text
    return NerSensitivityResult(is_sensitive=False, entities=[])
