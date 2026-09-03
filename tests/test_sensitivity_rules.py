"""Tests for expanded sensitivity regex rules."""

from packages.sensitivity_gate.rules import (
    check_conversation_sensitivity,
    check_latest_user_sensitivity,
    check_sensitivity,
)

pytestmark = __import__("pytest").mark.skipif(
    not __import__(
        "packages.sensitivity_gate.ner_classifier", fromlist=["ner_available"]
    ).ner_available(),
    reason="spacy model not installed",
)


def test_loose_phone_number_phrase_flags_sensitive() -> None:
    prompt = "hey my phone number is 58291089 can you help"
    result = check_sensitivity(prompt, use_ner=False)
    assert result.is_sensitive is True
    assert "phone_loose" in result.matched_rules


def test_name_intro_lowercase_flags_sensitive() -> None:
    prompt = "hey my name is rohan madan and I need help"
    result = check_sensitivity(prompt, use_ner=False)
    assert result.is_sensitive is True
    assert "name_intro" in result.matched_rules


def test_i_am_trying_is_not_sensitive() -> None:
    prompt = "I am trying to build a REST API in Python"
    result = check_sensitivity(prompt, use_ner=True)
    assert result.is_sensitive is False


def test_tech_terms_are_not_sensitive_with_ner() -> None:
    prompts = [
        "Write a function to sort a list in Python",
        "Compare SQL and NoSQL databases",
        "Design a GitHub Actions workflow",
    ]
    for prompt in prompts:
        result = check_sensitivity(prompt, use_ner=True)
        assert result.is_sensitive is False, prompt


def test_real_org_names_still_flag_with_ner() -> None:
    result = check_sensitivity(
        "Analyze Memorial Hospital security policies",
        use_ner=True,
    )
    assert result.is_sensitive is True
    assert any(rule.startswith("ner:") for rule in result.matched_rules)


def test_assistant_names_do_not_flag_follow_up_user_message() -> None:
    messages = [
        {"role": "user", "content": "hey"},
        {"role": "assistant", "content": "Hello Rohan Madan! How can I help?"},
        {"role": "user", "content": "hi"},
    ]
    conversation = check_conversation_sensitivity(messages, use_ner=True)
    latest = check_latest_user_sensitivity(messages, use_ner=True)
    assert conversation.is_sensitive is False
    assert latest.is_sensitive is False


def test_earlier_user_pii_keeps_conversation_sensitive() -> None:
    messages = [
        {"role": "user", "content": "hey my name is rohan madan"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "hi"},
    ]
    conversation = check_conversation_sensitivity(messages, use_ner=False)
    latest = check_latest_user_sensitivity(messages, use_ner=False)
    assert conversation.is_sensitive is True
    assert latest.is_sensitive is False
