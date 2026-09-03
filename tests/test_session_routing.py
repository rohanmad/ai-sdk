"""Tests for sticky chat session routing."""

from __future__ import annotations

from packages.routing_engine.decide import DecideOutput
from packages.routing_engine.session import SessionRouteStore, apply_sticky_routing


def _decision(
    target: str,
    *,
    complexity_level: str = "low",
    sensitivity: bool = False,
) -> DecideOutput:
    return DecideOutput(
        target=target,
        reason=f"test->{target}",
        complexity_level=complexity_level,
        sensitivity_flag=sensitivity,
        complexity_score=0.2 if complexity_level == "low" else 0.8,
        sensitivity_triggers=[],
    )


def test_sticky_reuses_target_for_follow_up() -> None:
    store = SessionRouteStore()
    first = _decision("small_local")
    second = _decision("cloud", complexity_level="high")

    apply_sticky_routing("sess-1", store, first)
    routed_second = apply_sticky_routing("sess-1", store, second)
    assert routed_second.target == "small_local"
    assert "session:sticky" in routed_second.reason


def test_sticky_upgrades_cloud_to_large_local_when_sensitive() -> None:
    store = SessionRouteStore()
    first = _decision("cloud", complexity_level="high")
    second = _decision("cloud", complexity_level="high", sensitivity=True)

    apply_sticky_routing("sess-2", store, first)
    routed_second = apply_sticky_routing("sess-2", store, second)
    assert routed_second.target == "large_local"
    assert "session:privacy_upgrade" in routed_second.reason
