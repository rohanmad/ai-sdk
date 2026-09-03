"""Tests for local prompt formatting."""

from packages.execution.prompt_format import (
    IM_END,
    QWEN_STOP_SEQUENCES,
    format_qwen_chat_messages,
    format_qwen_instruct_prompt,
)


def test_qwen_instruct_prompt_wraps_user_message() -> None:
    formatted = format_qwen_instruct_prompt("hey")
    assert formatted.startswith("<|im_start|>user\n")
    assert "hey" in formatted
    assert formatted.endswith("<|im_start|>assistant\n")


def test_qwen_stop_sequences_include_im_end() -> None:
    assert IM_END in QWEN_STOP_SEQUENCES
    assert "" not in QWEN_STOP_SEQUENCES


def test_qwen_chat_messages_include_prior_turns() -> None:
    formatted = format_qwen_chat_messages(
        [
            {"role": "user", "content": "My name is Alex"},
            {"role": "assistant", "content": "Hi Alex"},
            {"role": "user", "content": "What is my name?"},
        ]
    )
    assert "My name is Alex" in formatted
    assert "Hi Alex" in formatted
    assert "What is my name?" in formatted
    assert formatted.endswith("<|im_start|>assistant\n")
