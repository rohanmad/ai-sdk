"""Runs local models via llama.cpp (when configured) or mock mode for development."""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass
from typing import Any, Literal

from packages.execution.prompt_format import QWEN_STOP_SEQUENCES, format_qwen_instruct_prompt

LocalModelTier = Literal["small", "large"]


@dataclass
class LocalRunnerConfig:
    small_model_path: str = ""
    large_model_path: str = ""
    n_ctx: int = 2048
    n_threads: int | None = None


@dataclass
class LocalGenerateResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model_id: str
    latency_ms: float
    mock: bool


class LocalRunner:
    """Executes inference against small (1-3B) or large local quantized models."""

    def __init__(self, config: LocalRunnerConfig | None = None) -> None:
        self.config = config or LocalRunnerConfig()
        self._models: dict[LocalModelTier, Any] = {}

    def _resolve_path(self, tier: LocalModelTier) -> str:
        return self.config.small_model_path if tier == "small" else self.config.large_model_path

    def _load_model(self, tier: LocalModelTier) -> Any | None:
        if tier in self._models:
            return self._models[tier]

        path = self._resolve_path(tier)
        if not path:
            return None

        try:
            from llama_cpp import Llama  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "llama-cpp-python is required for real local inference. "
                "Install with: pip install llama-cpp-python"
            ) from exc

        model = Llama(
            model_path=path,
            n_ctx=self.config.n_ctx,
            n_threads=self.config.n_threads,
            verbose=False,
        )
        self._models[tier] = model
        return model

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def _mock_generate(self, prompt: str, tier: LocalModelTier, max_tokens: int) -> str:
        preview = prompt[:80].replace("\n", " ")
        if len(prompt) > 80:
            preview += "..."
        return (
            f"[mock-{tier}-local] Response to: {preview} "
            f"(max_tokens={max_tokens})"
        )

    def unload(self, tier: LocalModelTier | None = None) -> None:
        """Release loaded model(s) to free memory."""
        if tier is not None:
            model = self._models.pop(tier, None)
            if model is not None:
                del model
        else:
            for model in self._models.values():
                del model
            self._models.clear()
        gc.collect()

    def _generate_text(
        self,
        model: Any,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, dict]:
        """Run inference with chat template (Qwen instruct models need this)."""
        if hasattr(model, "create_chat_completion"):
            output = model.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            choice = output["choices"][0]
            message = choice.get("message") or {}
            text = (message.get("content") or choice.get("text") or "").strip()
            return text, output.get("usage", {})

        formatted = format_qwen_instruct_prompt(prompt)
        output = model(
            formatted,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False,
            stop=list(QWEN_STOP_SEQUENCES),
        )
        text = output["choices"][0]["text"].strip()
        return text, output.get("usage", {})

    def generate(
        self,
        prompt: str,
        *,
        tier: LocalModelTier = "small",
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> LocalGenerateResult:
        start = time.perf_counter()
        model = self._load_model(tier)
        model_id = f"local-{tier}"

        if model is None:
            text = self._mock_generate(prompt, tier, max_tokens)
            prompt_tokens = self._estimate_tokens(prompt)
            completion_tokens = self._estimate_tokens(text)
            latency_ms = (time.perf_counter() - start) * 1000
            return LocalGenerateResult(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_id=model_id,
                latency_ms=latency_ms,
                mock=True,
            )

        text, usage = self._generate_text(
            model,
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        prompt_tokens = int(usage.get("prompt_tokens", self._estimate_tokens(prompt)))
        completion_tokens = int(
            usage.get("completion_tokens", self._estimate_tokens(text))
        )
        latency_ms = (time.perf_counter() - start) * 1000

        return LocalGenerateResult(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_id=model_id,
            latency_ms=latency_ms,
            mock=False,
        )
