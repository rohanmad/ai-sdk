"""Chat prompt formatting for local instruct models."""


def format_qwen_instruct_prompt(prompt: str) -> str:
    """Wrap a user message in the Qwen2.5 chat template."""
    return (
        f"<|im_start|>user\n{prompt}\n"
        f"<|im_start|>assistant\n"
    )

QWEN_STOP_SEQUENCES = ("", "<|endoftext|>")
