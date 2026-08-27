"""Tests for hard-rule overrides in routing."""

from packages.routing_engine.decide import PolicyConfig, _apply_hard_rules


def test_hard_rule_overrides_cloud_for_sensitive_data() -> None:
    policy = PolicyConfig(
        hard_rules={"never_cloud_for_high_sensitivity": True},
        thresholds={},
        targets={},
        models={},
        dumb_routing={},
    )
    target, reason = _apply_hard_rules("cloud", sensitivity=True, policy=policy)
    assert target == "large_local"
    assert reason == "hard_rule:never_cloud_for_high_sensitivity"
