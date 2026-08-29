"""Tests for local prompt formatting."""

from packages.execution.prompt_format import QWEN_STOP_SEQUENCES, format_qwen_instruct_prompt

IM_END = "<|" + "im_end" + "|>"


def test_qwen_instruct_prompt_wraps_user_message() -> None:
    formatted = format_qwen_instruct_prompt("hey")
    assert formatted.startswith("<|im_start|>user\n")
    assert "hey" in formatted
    assert formatted.endswith("<|im_start|>assistant\n")


def test_qwen_stop_sequences_include_im_end() -> None:
    assert IM_END in QWEN_STOP_SEQUENCES
    assert "" not in QWEN_STOP_SEQUENCES
