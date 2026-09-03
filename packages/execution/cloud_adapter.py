"""Cloud API fallback adapter with an OpenAI-compatible interface."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterator


@dataclass
class CloudAdapterConfig:
    api_key: str | None = None
    base_url: str | None = None
    default_model: str = "gpt-4o-mini"


@dataclass
class CloudGenerateResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model_id: str
    latency_ms: float
    mock: bool
    finish_reason: str = "stop"


class CloudAdapter:
    """Invokes cloud LLM APIs when the routing policy allows."""

    def __init__(self, config: CloudAdapterConfig | None = None) -> None:
        self.config = config or CloudAdapterConfig()
        self._client = None

    def _get_api_key(self) -> str | None:
        return self.config.api_key or os.environ.get("OPENAI_API_KEY")

    def _get_client(self):
        if self._client is not None:
            return self._client

        api_key = self._get_api_key()
        if not api_key:
            return None

        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required for cloud inference. "
                "Install with: pip install openai"
            ) from exc

        self._client = OpenAI(api_key=api_key, base_url=self.config.base_url)
        return self._client

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def _mock_generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        *,
        turn_count: int = 1,
    ) -> str:
        preview = prompt[:80].replace("\n", " ")
        if len(prompt) > 80:
            preview += "..."
        turns = f"; turns={turn_count}" if turn_count > 1 else ""
        return (
            f"[mock-cloud:{model}] Response to: {preview} "
            f"(max_tokens={max_tokens}{turns})"
        )

    def _chat_messages(
        self,
        prompt: str,
        messages: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        if messages:
            return messages
        return [{"role": "user", "content": prompt}]

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        messages: list[dict[str, str]] | None = None,
    ) -> CloudGenerateResult:
        start = time.perf_counter()
        model_id = model or self.config.default_model
        client = self._get_client()
        chat_messages = self._chat_messages(prompt, messages)

        if client is None:
            text = self._mock_generate(
                prompt,
                model_id,
                max_tokens,
                turn_count=len(chat_messages),
            )
            prompt_tokens = self._estimate_tokens(
                "\n".join(m["content"] for m in chat_messages)
            )
            completion_tokens = self._estimate_tokens(text)
            latency_ms = (time.perf_counter() - start) * 1000
            return CloudGenerateResult(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_id=model_id,
                latency_ms=latency_ms,
                mock=True,
            )

        response = client.chat.completions.create(
            model=model_id,
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response.choices[0]
        text = choice.message.content or ""
        finish_reason = choice.finish_reason or "stop"
        usage = response.usage
        prompt_tokens = (
            usage.prompt_tokens
            if usage
            else self._estimate_tokens("\n".join(m["content"] for m in chat_messages))
        )
        completion_tokens = (
            usage.completion_tokens if usage else self._estimate_tokens(text)
        )
        latency_ms = (time.perf_counter() - start) * 1000

        return CloudGenerateResult(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_id=model_id,
            latency_ms=latency_ms,
            mock=False,
            finish_reason=finish_reason,
        )

    def generate_stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        messages: list[dict[str, str]] | None = None,
    ) -> Iterator[str]:
        model_id = model or self.config.default_model
        client = self._get_client()
        chat_messages = self._chat_messages(prompt, messages)

        if client is None:
            text = self._mock_generate(
                prompt,
                model_id,
                max_tokens,
                turn_count=len(chat_messages),
            )
            for word in text.split():
                yield word + " "
            return

        stream = client.chat.completions.create(
            model=model_id,
            messages=chat_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
