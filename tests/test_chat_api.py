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


def test_chat_accepts_message_history(chat_client: TestClient) -> None:
    response = chat_client.post(
        "/api/chat",
        json={
            "messages": [
                {"role": "user", "content": "Remember the number 42."},
                {"role": "assistant", "content": "Got it."},
                {"role": "user", "content": "What number did I mention?"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["text"]
    assert "turns=3" in data["text"] or "42" in data["text"].lower()


def test_chat_stream_returns_done_event(chat_client: TestClient) -> None:
    response = chat_client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "Say hello"}],
            "stream": True,
        },
    )
    assert response.status_code == 200
    body = response.text
    assert "data: " in body
    assert '"type": "done"' in body or '"type":"done"' in body


def test_chat_session_sticks_target(chat_client: TestClient) -> None:
    session_id = "test-session-stick-001"
    first = chat_client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "messages": [{"role": "user", "content": "Short hello"}],
        },
    )
    second = chat_client.post(
        "/api/chat",
        json={
            "session_id": session_id,
            "messages": [
                {"role": "user", "content": "Short hello"},
                {"role": "assistant", "content": "Hi"},
                {
                    "role": "user",
                    "content": (
                        "Design a distributed system with consensus, replication, "
                        "and failure recovery across regions. "
                        + ("detail " * 120)
                    ),
                },
            ],
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_target = first.json()["target"]
    second_data = second.json()
    if first_target != "cloud":
        assert second_data["target"] == first_target
        assert "session:sticky" in second_data["reason"]
