"""Chat prompt formatting for local instruct models."""

from __future__ import annotations

from typing import Any

IM_END = "<|" + "im_end" + "|>"
QWEN_STOP_SEQUENCES = (IM_END, "<|endoftext|>")


def format_qwen_instruct_prompt(prompt: str) -> str:
    """Wrap a single user message in the Qwen2.5 chat template."""
    return format_qwen_chat_messages([{"role": "user", "content": prompt}])


def format_qwen_chat_messages(messages: list[dict[str, Any]]) -> str:
    """Format a multi-turn chat for Qwen2.5 instruct models."""
    parts: list[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        parts.append(f"<|im_start|>{role}\n{content}{IM_END}")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)
