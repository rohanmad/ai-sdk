"""Public SDK — Router.init(), router.generate_text()."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from packages.execution.cloud_adapter import CloudAdapter, CloudAdapterConfig
from packages.execution.local_runner import LocalRunner, LocalRunnerConfig
from packages.routing_engine.decide import DecideInput, DecideOutput, PolicyConfig, decide
from packages.routing_engine.session import SessionRouteStore, apply_sticky_routing
from packages.sensitivity_gate.rules import (
    check_conversation_sensitivity,
    check_latest_user_sensitivity,
)
from packages.sdk.types import (
    GenerateTextChoice,
    GenerateTextRequest,
    GenerateTextResponse,
    GenerateTextUsage,
    RoutingDecision,
    RoutingTarget,
)
from telemetry.logger import RoutingLogEntry, TelemetryLogger

# Cloud baseline cost estimate (USD per 1K tokens) for savings calculation
_CLOUD_COST_PER_1K_TOKENS = 0.00015


@dataclass
class RouterConfig:
    policy_path: str | Path = "config/policy.yaml"
    telemetry_db: str | Path = "telemetry/routing.db"
    small_model_path: str = ""
    large_model_path: str = ""
    cloud_api_key: str | None = None
    cloud_model: str = "gpt-4o-mini"


class Router:
    """Adaptive inference router with OpenAI-compatible generate_text API."""

    def __init__(self, config: RouterConfig | None = None) -> None:
        self.config = config or RouterConfig()
        policy_path = Path(self.config.policy_path)
        if not policy_path.is_absolute():
            policy_path = Path(__file__).resolve().parents[2] / policy_path
        self.policy = PolicyConfig.load(policy_path)

        models = self.policy.models
        small_path = self.config.small_model_path or models.get("small_local", {}).get(
            "path", ""
        )
        large_path = self.config.large_model_path or models.get("large_local", {}).get(
            "path", ""
        )

        self.local = LocalRunner(
            LocalRunnerConfig(
                small_model_path=small_path,
                large_model_path=large_path,
            )
        )
        cloud_model = (
            self.config.cloud_model
            or models.get("cloud", {}).get("model_id", "gpt-4o-mini")
        )
        self.cloud = CloudAdapter(
            CloudAdapterConfig(
                api_key=self.config.cloud_api_key,
                default_model=cloud_model,
            )
        )

        telemetry_path = Path(self.config.telemetry_db)
        if not telemetry_path.is_absolute():
            telemetry_path = Path(__file__).resolve().parents[2] / telemetry_path
        self.telemetry = TelemetryLogger(telemetry_path)

    @classmethod
    def init(cls, config: RouterConfig | None = None) -> Router:
        return cls(config)

    def _estimate_cost_saved(
        self, target: RoutingTarget, total_tokens: int
    ) -> float | None:
        if target == "cloud":
            return 0.0
        baseline = (total_tokens / 1000) * _CLOUD_COST_PER_1K_TOKENS
        return round(baseline, 6)

    def _route(
        self,
        request: GenerateTextRequest,
        session_store: SessionRouteStore | None,
    ) -> tuple[DecideOutput, list[str], bool, list[str]]:
        conversation = check_conversation_sensitivity(
            request.messages,
            prompt=request.prompt,
        )
        latest = check_latest_user_sensitivity(
            request.messages,
            prompt=request.prompt,
        )
        decision_out = decide(
            DecideInput(
                prompt=request.prompt,
                sensitivity_flag=conversation.is_sensitive,
                sensitivity_triggers=conversation.triggers,
                complexity_score=0.0,
            ),
            self.policy,
        )
        if session_store and request.session_id:
            decision_out = apply_sticky_routing(
                request.session_id,
                session_store,
                decision_out,
            )
        return (
            decision_out,
            latest.triggers,
            latest.is_sensitive,
            conversation.triggers,
        )

    def _execute(
        self,
        target: RoutingTarget,
        prompt: str,
        max_tokens: int,
        temperature: float,
        messages: list[dict[str, str]] | None = None,
    ):
        if target == "small_local":
            return self.local.generate(
                prompt,
                tier="small",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
        if target == "large_local":
            return self.local.generate(
                prompt,
                tier="large",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
        return self.cloud.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )

    def _stream_execute(
        self,
        target: RoutingTarget,
        prompt: str,
        max_tokens: int,
        temperature: float,
        messages: list[dict[str, str]] | None = None,
    ) -> Iterator[str]:
        if target == "small_local":
            yield from self.local.generate_stream(
                prompt,
                tier="small",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
            return
        if target == "large_local":
            yield from self.local.generate_stream(
                prompt,
                tier="large",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
            return
        yield from self.cloud.generate_stream(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )

    def _log_request(
        self,
        *,
        request_id: str,
        request: GenerateTextRequest,
        decision_out: DecideOutput,
        sensitivity_triggers: list[str],
        message_sensitivity_flag: bool,
        latency_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        mock_execution: bool,
    ) -> None:
        total_tokens = prompt_tokens + completion_tokens
        cost_saved = self._estimate_cost_saved(decision_out.target, total_tokens)
        self.telemetry.log(
            RoutingLogEntry(
                request_id=request_id,
                target=decision_out.target,
                reason=decision_out.reason,
                complexity_score=decision_out.complexity_score,
                sensitivity_flag=message_sensitivity_flag,
                sensitivity_triggers=sensitivity_triggers,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_saved_usd=cost_saved,
                mock_execution=mock_execution,
                prompt_preview=request.prompt[:120],
            )
        )

    def generate_text(
        self,
        request: GenerateTextRequest,
        *,
        session_store: SessionRouteStore | None = None,
    ) -> GenerateTextResponse:
        """Route and execute inference; returns OpenAI-compatible response shape."""
        pipeline_start = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        decision_out, sensitivity_triggers, message_sensitivity_flag, _ = (
            self._route(request, session_store)
        )

        result = self._execute(
            decision_out.target,
            request.prompt,
            request.max_tokens,
            request.temperature,
            messages=request.messages,
        )

        total_tokens = result.prompt_tokens + result.completion_tokens
        latency_ms = (time.perf_counter() - pipeline_start) * 1000

        self._log_request(
            request_id=request_id,
            request=request,
            decision_out=decision_out,
            sensitivity_triggers=sensitivity_triggers,
            message_sensitivity_flag=message_sensitivity_flag,
            latency_ms=latency_ms,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            mock_execution=result.mock,
        )

        routing = RoutingDecision(
            target=decision_out.target,
            reason=decision_out.reason,
            complexity_score=decision_out.complexity_score,
            sensitivity_flag=message_sensitivity_flag,
            sensitivity_triggers=sensitivity_triggers,
        )

        return GenerateTextResponse(
            id=request_id,
            object="text.completion",
            created=int(time.time()),
            model=result.model_id,
            choices=[
                GenerateTextChoice(
                    index=0,
                    text=result.text,
                    finish_reason=getattr(result, "finish_reason", "stop"),
                )
            ],
            usage=GenerateTextUsage(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=total_tokens,
            ),
            routing=routing,
            latency_ms=latency_ms,
            estimated_cost_saved_usd=self._estimate_cost_saved(
                decision_out.target, total_tokens
            ),
        )

    def generate_text_stream(
        self,
        request: GenerateTextRequest,
        *,
        session_store: SessionRouteStore | None = None,
    ) -> Iterator[dict[str, object]]:
        """Yield token events, then a final done event with routing metadata."""
        pipeline_start = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        decision_out, sensitivity_triggers, message_sensitivity_flag, _ = (
            self._route(request, session_store)
        )

        parts: list[str] = []
        for token in self._stream_execute(
            decision_out.target,
            request.prompt,
            request.max_tokens,
            request.temperature,
            messages=request.messages,
        ):
            parts.append(token)
            yield {"type": "token", "text": token}

        text = "".join(parts)
        prompt_tokens = max(1, len(request.prompt.split()))
        completion_tokens = max(1, len(text.split()))
        latency_ms = (time.perf_counter() - pipeline_start) * 1000
        mock_execution = "[mock-" in text or "[mock-cloud:" in text

        self._log_request(
            request_id=request_id,
            request=request,
            decision_out=decision_out,
            sensitivity_triggers=sensitivity_triggers,
            message_sensitivity_flag=message_sensitivity_flag,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            mock_execution=mock_execution,
        )

        yield {
            "type": "done",
            "request_id": request_id,
            "text": text,
            "target": decision_out.target,
            "reason": decision_out.reason,
            "complexity_score": decision_out.complexity_score,
            "sensitivity_flag": message_sensitivity_flag,
            "sensitivity_triggers": sensitivity_triggers,
            "latency_ms": round(latency_ms, 2),
            "model": (
                "local-small"
                if decision_out.target == "small_local"
                else "local-large"
                if decision_out.target == "large_local"
                else self.cloud.config.default_model
            ),
            "mock_execution": mock_execution,
            "finish_reason": "stop",
        }
