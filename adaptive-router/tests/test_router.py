"""Tests for the adaptive inference router."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from packages.routing_engine.decide import DecideInput, PolicyConfig, decide
from packages.sdk.router import Router, RouterConfig
from packages.sdk.types import GenerateTextRequest
from packages.sensitivity_gate.rules import check_sensitivity

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@pytest.fixture
def policy() -> PolicyConfig:
    return PolicyConfig.load(CONFIG_DIR / "policy.yaml")


@pytest.fixture
def dumb_policy() -> PolicyConfig:
    """Policy with character-count routing enabled (for legacy / fallback tests)."""
    return PolicyConfig.load(CONFIG_DIR / "policy.dumb.yaml")


def test_sensitivity_detects_email() -> None:
    result = check_sensitivity("Contact me at alice@example.com")
    assert result.is_sensitive is True
    assert "email" in result.matched_rules


def test_sensitivity_ignores_benign_prompt() -> None:
    result = check_sensitivity("What is the capital of France?")
    assert result.is_sensitive is False
    assert result.matched_rules == []


def test_dumb_routing_short_prompt_goes_local(dumb_policy: PolicyConfig) -> None:
    output = decide(
        DecideInput(
            prompt="short prompt",
            sensitivity_flag=False,
            sensitivity_triggers=[],
            complexity_score=0.0,
        ),
        dumb_policy,
    )
    assert output.target == "small_local"
    assert "dumb_routing" in output.reason


def test_dumb_routing_long_prompt_goes_cloud(dumb_policy: PolicyConfig) -> None:
    output = decide(
        DecideInput(
            prompt="x" * 600,
            sensitivity_flag=False,
            sensitivity_triggers=[],
            complexity_score=0.0,
        ),
        dumb_policy,
    )
    assert output.target == "cloud"
    assert "dumb_routing" in output.reason


def test_sensitive_long_prompt_never_goes_to_cloud(dumb_policy: PolicyConfig) -> None:
    output = decide(
        DecideInput(
            prompt="x" * 600,
            sensitivity_flag=True,
            sensitivity_triggers=["SSN-shaped pattern detected"],
            complexity_score=0.0,
        ),
        dumb_policy,
    )
    assert output.target == "large_local"
    assert output.sensitivity_flag is True
    assert "sensitivity=HIGH" in output.reason


def test_router_end_to_end_mock_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "routing.db"
        router = Router.init(
            RouterConfig(
                policy_path=CONFIG_DIR / "policy.dumb.yaml",
                telemetry_db=db_path,
                small_model_path="",
                large_model_path="",
            )
        )

        short = router.generate_text(
            GenerateTextRequest(prompt="Hello, world!", max_tokens=32)
        )
        assert short.routing.target == "small_local"
        assert short.choices[0].text.startswith("[mock-small-local]")

        long = router.generate_text(
            GenerateTextRequest(prompt="a" * 600, max_tokens=32)
        )
        assert long.routing.target == "cloud"
        assert "[mock-cloud:" in long.choices[0].text

        summary = router.telemetry.summary()
        assert summary["total_requests"] == 2
