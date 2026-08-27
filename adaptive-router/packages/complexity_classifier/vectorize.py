"""Convert ComplexityFeatures to a numeric vector for sklearn."""

from __future__ import annotations

import numpy as np

from packages.complexity_classifier.features import ComplexityFeatures, extract_features

FEATURE_NAMES = (
    "char_length",
    "word_count",
    "question_marks",
    "reasoning_keyword_hits",
    "code_block_present",
    "multi_step_hint",
)


def features_to_array(features: ComplexityFeatures) -> np.ndarray:
    return np.array(
        [
            features.char_length,
            features.word_count,
            features.question_marks,
            features.reasoning_keyword_hits,
            int(features.code_block_present),
            int(features.multi_step_hint),
        ],
        dtype=np.float64,
    )


def prompt_to_array(prompt: str) -> np.ndarray:
    return features_to_array(extract_features(prompt))
