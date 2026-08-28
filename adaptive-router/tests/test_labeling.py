"""Tests for improved labeling logic."""

from __future__ import annotations

from packages.complexity_classifier.labeling import (
    answer_number_match,
    answer_token_overlap,
    extract_key_phrase,
    is_short_factual_prompt,
    substring_answer_match,
    word_count,
)

PURPLE_SMALL = "When you mix red and blue in equal amounts, you get purple."
PURPLE_LARGE = (
    "By mixing red and blue, you get purple. More specifically, it would be a "
    "shade of purple known as magenta or fuchsia."
)
ROWLING_SMALL = "J.K. Rowling wrote the Harry Potter series."
ROWLING_LARGE = (
    'The Harry Potter series was written by British author J.K. Rowling. '
    'She began writing the series in 1992.'
)
HEART_SMALL = "The heart pumps blood through the body."
HEART_LARGE = (
    "The organ that pumps blood through the body is the heart. "
    "The heart is a muscular organ located in the chest."
)
CM_SMALL = (
    "To determine how many centimeters are in one meter, we need to understand "
    "the relationship between meters and centimeters. By definition, 1 meter is "
    "equal to 100 centimeters."
)
CM_LARGE = (
    "There are 100 centimeters in one meter. This conversion is based on the "
    "metric system where centi- means one-hundredth."
)
HOURS_SMALL = (
    "To determine how many minutes are in three hours, we can follow these steps: "
    "There are 60 minutes in one hour. Since there are 60 minutes"
)
HOURS_LARGE = (
    "There are 60 minutes in one hour. Therefore, in three hours, there are "
    "180 minutes. So, there are 180 minutes in three hours."
)


def test_word_count():
    assert word_count("The answer is twelve") == 4


def test_extract_key_phrase_strips_prefix():
    assert extract_key_phrase("The answer is 12, since sqrt(144)=12.") == "12"


def test_extract_key_phrase_you_get():
    assert extract_key_phrase(PURPLE_LARGE) == "purple"


def test_substring_match_numeric():
    assert substring_answer_match("12", "The answer is 12, since the square root of 144 is 12.")


def test_substring_match_fact():
    assert substring_answer_match("water", "Water.")


def test_substring_match_purple():
    assert substring_answer_match(PURPLE_SMALL, PURPLE_LARGE)


def test_substring_match_rowling():
    assert substring_answer_match(ROWLING_SMALL, ROWLING_LARGE)


def test_substring_match_heart():
    assert substring_answer_match(HEART_SMALL, HEART_LARGE)


def test_factual_number_match_centimeters():
    prompt = "How many centimeters are in one meter?"
    assert is_short_factual_prompt(prompt)
    assert substring_answer_match(CM_SMALL, CM_LARGE, prompt)


def test_factual_number_match_does_not_flip_incomplete_hours():
    prompt = "How many minutes are in three hours?"
    assert is_short_factual_prompt(prompt)
    assert not answer_number_match(HOURS_SMALL, HOURS_LARGE)
    assert not substring_answer_match(HOURS_SMALL, HOURS_LARGE, prompt)


def test_answer_token_overlap():
    assert answer_token_overlap(HEART_SMALL, HEART_LARGE)


def test_substring_match_fails_different_answers():
    assert not substring_answer_match("Paris", "London is the capital of England.")
