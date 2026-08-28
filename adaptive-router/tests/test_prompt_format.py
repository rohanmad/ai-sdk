"""Tests for local prompt formatting."""

from packages.execution.prompt_format import format_qwen_instruct_prompt


def test_qwen_instruct_prompt_wraps_user_message() -> None:
    formatted = format_qwen_instruct_prompt("hey")
    assert formatted.startswith("<|im_start|>user\n")
    assert "hey" in formatted
    assert formatted.endswith("<|im_start|>assistant\n")
