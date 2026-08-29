"""Routing tests for classifier-based policy."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest
import yaml
from sklearn.linear_model import LogisticRegression

from packages.complexity_classifier.vectorize import prompt_to_array
from packages.routing_engine.decide import DecideInput, PolicyConfig, decide
from packages.sensitivity_gate.rules import check_sensitivity

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "packages" / "complexity_classifier" / "model.pkl"
POLICY_PATH = ROOT / "config" / "policy.yaml"


@pytest.fixture
def classifier_policy(tmp_path: Path) -> PolicyConfig:
    with open(POLICY_PATH, encoding="utf-8") as f:
        policy_data = yaml.safe_load(f)
    policy_data["dumb_routing"]["enabled"] = False
    test_policy = tmp_path / "policy.yaml"
    test_policy.write_text(yaml.dump(policy_data), encoding="utf-8")
    return PolicyConfig.load(test_policy)


def test_classifier_path_used_when_dumb_routing_disabled(
    classifier_policy: PolicyConfig,
) -> None:
    if not MODEL_PATH.exists():
        pytest.skip("model.pkl not trained yet")

    output = decide(
        DecideInput(
            prompt="What is the capital of France?",
            sensitivity_flag=False,
            sensitivity_triggers=[],
            complexity_score=0.0,
        ),
        classifier_policy,
    )
    assert "classifier:" in output.reason
    assert "dumb_routing" not in output.reason
    assert output.target in {"small_local", "large_local", "cloud"}


def test_high_complexity_and_sensitive_routes_to_large_local(
    classifier_policy: PolicyConfig,
) -> None:
    if not MODEL_PATH.exists():
        pytest.skip("model.pkl not trained yet")

    prompt = (
        "Design a data pipeline that processes SSN 123-45-6789 "
        "for compliance reporting and audit trails."
    )
    sensitivity = check_sensitivity(prompt)
    assert sensitivity.is_sensitive is True

    output = decide(
        DecideInput(
            prompt=prompt,
            sensitivity_flag=sensitivity.is_sensitive,
            sensitivity_triggers=sensitivity.triggers,
            complexity_score=0.0,
        ),
        classifier_policy,
    )
    assert output.complexity_level == "high"
    assert output.sensitivity_flag is True
    assert output.target == "large_local"
    assert "sensitivity=HIGH" in output.reason
    assert "complexity=HIGH" in output.reason
