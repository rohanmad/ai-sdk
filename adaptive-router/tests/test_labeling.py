"""Tests for improved labeling logic."""

from __future__ import annotations

from packages.complexity_classifier.labeling import (
    extract_key_phrase,
    substring_answer_match,
    word_count,
)


def test_word_count():
    assert word_count("The answer is twelve") == 4


def test_extract_key_phrase_strips_prefix():
    assert extract_key_phrase("The answer is 12, since sqrt(144)=12.") == "12"


def test_substring_match_numeric():
    assert substring_answer_match("12", "The answer is 12, since the square root of 144 is 12.")


def test_substring_match_fact():
    assert substring_answer_match("water", "Water.")


def test_substring_match_fails_different_answers():
    assert not substring_answer_match("Paris", "London is the capital of England.")
