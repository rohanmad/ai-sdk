"""OpenAI-compatible request/response types for the adaptive router."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RoutingTarget = Literal["small_local", "large_local", "cloud"]


@dataclass
class GenerateTextRequest:
    prompt: str
    model: str | None = None
    max_tokens: int = 256
    temperature: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerateTextChoice:
    index: int
    text: str
    finish_reason: str = "stop"


@dataclass
class GenerateTextUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class RoutingDecision:
    target: RoutingTarget
    reason: str
    complexity_score: float
    sensitivity_flag: bool
    sensitivity_triggers: list[str] = field(default_factory=list)


@dataclass
class GenerateTextResponse:
    id: str
    object: str
    created: int
    model: str
    choices: list[GenerateTextChoice]
    usage: GenerateTextUsage
    routing: RoutingDecision
    latency_ms: float
    estimated_cost_saved_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": c.index,
                    "text": c.text,
                    "finish_reason": c.finish_reason,
                }
                for c in self.choices
            ],
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
            },
            "routing": {
                "target": self.routing.target,
                "reason": self.routing.reason,
                "complexity_score": self.routing.complexity_score,
                "sensitivity_flag": self.routing.sensitivity_flag,
                "sensitivity_triggers": self.routing.sensitivity_triggers,
            },
            "latency_ms": self.latency_ms,
            "estimated_cost_saved_usd": self.estimated_cost_saved_usd,
        }
