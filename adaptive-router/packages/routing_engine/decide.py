"""Combines sensitivity + complexity signals into a routing decision."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from packages.sdk.types import RoutingTarget

ComplexityLevel = Literal["low", "high"]


@dataclass
class PolicyConfig:
    hard_rules: dict[str, bool]
    thresholds: dict[str, Any]
    targets: dict[str, RoutingTarget]
    models: dict[str, Any]
    dumb_routing: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> PolicyConfig:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls(
            hard_rules=raw.get("hard_rules", {}),
            thresholds=raw.get("thresholds", {}),
            targets=raw.get("targets", {}),
            models=raw.get("models", {}),
            dumb_routing=raw.get("dumb_routing", {}),
        )


@dataclass
class DecideInput:
    prompt: str
    sensitivity_flag: bool
    sensitivity_triggers: list[str]
    complexity_score: float


@dataclass
class DecideOutput:
    target: RoutingTarget
    reason: str
    complexity_level: ComplexityLevel
    sensitivity_flag: bool
    complexity_score: float
    sensitivity_triggers: list[str]


def _complexity_level(score: float, policy: PolicyConfig) -> ComplexityLevel:
    thresholds = policy.thresholds.get("complexity", {})
    low_max = float(thresholds.get("low_max", 0.45))
    high_min = float(thresholds.get("high_min", 0.55))

    if score <= low_max:
        return "low"
    if score >= high_min:
        return "high"
    # Ambiguous band — conservative default
    return "low"


def _policy_target(
    complexity: ComplexityLevel,
    sensitivity: bool,
    policy: PolicyConfig,
) -> RoutingTarget:
    if complexity == "low" and not sensitivity:
        return policy.targets.get("low_complexity_low_sensitivity", "small_local")
    if complexity == "low" and sensitivity:
        return policy.targets.get("low_complexity_high_sensitivity", "small_local")
    if complexity == "high" and not sensitivity:
        return policy.targets.get("high_complexity_low_sensitivity", "cloud")
    return policy.targets.get("high_complexity_high_sensitivity", "large_local")


def _apply_hard_rules(
    target: RoutingTarget,
    sensitivity: bool,
    policy: PolicyConfig,
) -> tuple[RoutingTarget, str | None]:
    if (
        policy.hard_rules.get("never_cloud_for_high_sensitivity")
        and sensitivity
        and target == "cloud"
    ):
        return "large_local", "hard_rule:never_cloud_for_high_sensitivity"
    return target, None


def decide(input_data: DecideInput, policy: PolicyConfig) -> DecideOutput:
    """
    Pure policy logic — combines signals into a 2x2 routing decision.

    When dumb_routing.enabled is true (build step 1), uses a simple length
    heuristic for complexity so both local and cloud paths can be exercised
    without a trained classifier.
    """
    dumb = policy.dumb_routing or {}
    if dumb.get("enabled"):
        threshold = int(dumb.get("cloud_char_threshold", 500))
        if len(input_data.prompt) >= threshold:
            complexity_score = 0.8
            complexity_level: ComplexityLevel = "high"
            reason_prefix = (
                f"dumb_routing:prompt_length>={threshold} "
                f"(chars={len(input_data.prompt)})"
            )
        else:
            complexity_score = 0.2
            complexity_level = "low"
            reason_prefix = (
                f"dumb_routing:prompt_length<{threshold} "
                f"(chars={len(input_data.prompt)})"
            )
    else:
        complexity_score = input_data.complexity_score
        complexity_level = _complexity_level(complexity_score, policy)
        reason_prefix = f"complexity_score={complexity_score:.3f}"

    target = _policy_target(complexity_level, input_data.sensitivity_flag, policy)
    hard_override, hard_reason = _apply_hard_rules(
        target, input_data.sensitivity_flag, policy
    )
    if hard_override != target:
        target = hard_override
        reason = f"{reason_prefix}; {hard_reason}; forced_local"
    else:
        sensitivity_label = "HIGH" if input_data.sensitivity_flag else "LOW"
        reason = (
            f"{reason_prefix}; complexity={complexity_level.upper()}; "
            f"sensitivity={sensitivity_label} -> {target}"
        )

    return DecideOutput(
        target=target,
        reason=reason,
        complexity_level=complexity_level,
        sensitivity_flag=input_data.sensitivity_flag,
        complexity_score=complexity_score,
        sensitivity_triggers=input_data.sensitivity_triggers,
    )
