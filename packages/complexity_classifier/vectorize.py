"""Convert hand-crafted + embedding features to a numeric vector for sklearn."""

from __future__ import annotations

import numpy as np

from packages.complexity_classifier.features import (
    EMBEDDING_DIM,
    ComplexityFeatures,
    embed_prompt,
    embed_prompts,
    extract_features,
)

HANDCRAFTED_FEATURE_NAMES = (
    "char_length",
    "word_count",
    "question_marks",
    "reasoning_keyword_hits",
    "code_block_present",
    "multi_step_hint",
    "open_ended_starter",
    "imperative_multi_step",
    "factual_pattern",
    "length_bucket_short",
    "length_bucket_medium",
    "length_bucket_long",
)

# Backward-compatible alias
FEATURE_NAMES = HANDCRAFTED_FEATURE_NAMES
LEGACY_HANDCRAFTED_DIM = 6


def handcrafted_to_array(features: ComplexityFeatures) -> np.ndarray:
    return np.array(
        [
            features.char_length,
            features.word_count,
            features.question_marks,
            features.reasoning_keyword_hits,
            int(features.code_block_present),
            int(features.multi_step_hint),
            int(features.open_ended_starter),
            int(features.imperative_multi_step),
            int(features.factual_pattern),
            int(features.length_bucket_short),
            int(features.length_bucket_medium),
            int(features.length_bucket_long),
        ],
        dtype=np.float64,
    )


def features_to_array(features: ComplexityFeatures) -> np.ndarray:
    return handcrafted_to_array(features)


def prompt_to_handcrafted_array(prompt: str) -> np.ndarray:
    return handcrafted_to_array(extract_features(prompt))


def prompt_to_array(prompt: str, *, use_embeddings: bool = True) -> np.ndarray:
    handcrafted = prompt_to_handcrafted_array(prompt)
    if not use_embeddings:
        return handcrafted
    embedding = embed_prompt(prompt)
    return np.concatenate([handcrafted, embedding])


def prompts_to_matrix(
    prompts: list[str],
    *,
    use_embeddings: bool = True,
) -> np.ndarray:
    handcrafted = np.vstack([prompt_to_handcrafted_array(p) for p in prompts])
    if not use_embeddings:
        return handcrafted
    embeddings = embed_prompts(prompts)
    if embeddings.shape[1] != EMBEDDING_DIM:
        raise ValueError(f"Expected {EMBEDDING_DIM}-dim embeddings, got {embeddings.shape[1]}")
    return np.hstack([handcrafted, embeddings])
