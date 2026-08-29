"""Tests for the chat API endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.sdk.router import RouterConfig
from telemetry.dashboard.web.app import create_app
from telemetry.logger import TelemetryLogger

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


@pytest.fixture
def chat_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "routing.db"
    policy_path = CONFIG_DIR / "policy.dumb.yaml"
    router_config = RouterConfig(
        policy_path=policy_path,
        telemetry_db=db_path,
        small_model_path="",
        large_model_path="",
    )
    return TestClient(create_app(db_path, policy_path=policy_path, router_config=router_config))


def test_chat_returns_expected_shape(chat_client: TestClient) -> None:
    response = chat_client.post(
        "/api/chat",
        json={"prompt": "Hello, what is two plus two?"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["text"]
    assert data["target"] in {"small_local", "large_local", "cloud"}
    assert isinstance(data["reason"], str) and data["reason"]
    assert isinstance(data["complexity_score"], (int, float))
    assert isinstance(data["sensitivity_flag"], bool)
    assert isinstance(data["sensitivity_triggers"], list)
    assert isinstance(data["latency_ms"], (int, float))
    assert data["request_id"].startswith("req_")


def test_chat_logs_to_telemetry(chat_client: TestClient, tmp_path: Path) -> None:
    db_path = tmp_path / "routing.db"
    before = TelemetryLogger(db_path).summary()["total_requests"]

    response = chat_client.post(
        "/api/chat",
        json={"prompt": "Quick test prompt for telemetry logging."},
    )
    assert response.status_code == 200

    after = TelemetryLogger(db_path).summary()["total_requests"]
    assert after == before + 1


def test_chat_sensitive_prompt_flags_and_avoids_cloud_for_long(
    chat_client: TestClient,
) -> None:
    response = chat_client.post(
        "/api/chat",
        json={
            "prompt": (
                "Contact alice@example.com about the confidential review. "
                + "x" * 520
            ),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sensitivity_flag"] is True
    assert data["target"] != "cloud"


def test_chat_page_served(chat_client: TestClient) -> None:
    response = chat_client.get("/chat")
    assert response.status_code == 200
    assert "Adaptive Router" in response.text
