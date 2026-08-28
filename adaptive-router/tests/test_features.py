"""Tests for prompt-pattern complexity features."""

from __future__ import annotations

from packages.complexity_classifier.features import extract_features


def test_open_ended_starter():
    feats = extract_features("Design a rate limiter for an API.")
    assert feats.open_ended_starter is True
    assert feats.factual_pattern is False


def test_factual_pattern():
    feats = extract_features("Who wrote the Harry Potter series?")
    assert feats.factual_pattern is True
    assert feats.open_ended_starter is False


def test_imperative_multi_step():
    feats = extract_features("A user reports slow checkout. List a step-by-step debugging plan.")
    assert feats.imperative_multi_step is True


def test_length_buckets():
    short = extract_features("What is 2+2?")
    long = extract_features(
        "Compare on-device inference vs cloud inference for a health app with strict latency requirements and privacy constraints."
    )
    assert short.length_bucket_short is True
    assert long.length_bucket_long is True


def test_reasoning_keyword_hits_distinct_from_starter():
    # explain anywhere vs line-start design/debug
    explain = extract_features("Explain how photosynthesis works.")
    design = extract_features("Design a caching strategy.")
    assert explain.reasoning_keyword_hits >= 1
    assert explain.open_ended_starter is False
    assert design.open_ended_starter is True
