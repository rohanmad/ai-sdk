"""Test classifier-based routing when dumb_routing is disabled."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest
import yaml
from sklearn.linear_model import LogisticRegression

from packages.complexity_classifier.vectorize import prompt_to_array
from packages.routing_engine.decide import DecideInput, PolicyConfig, decide

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
