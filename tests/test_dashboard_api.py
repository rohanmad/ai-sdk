"""Tests for the web telemetry dashboard API."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from telemetry.dashboard.web.app import create_app
from telemetry.logger import RoutingLogEntry, TelemetryLogger


def _seed_db(db_path: Path, n: int = 5) -> None:
    logger = TelemetryLogger(db_path)
    targets = ["small_local", "cloud", "small_local", "large_local", "cloud"]
    for i in range(n):
        target = targets[i % len(targets)]
        logger.log(
            RoutingLogEntry(
                request_id=f"req_test_{i:03d}",
                target=target,
                reason=f"test reason {i}",
                complexity_score=0.1 * i,
                sensitivity_flag=i % 3 == 0,
                sensitivity_triggers=["email"] if i % 3 == 0 else [],
                latency_ms=10.0 + i,
                prompt_tokens=20 + i,
                completion_tokens=40 + i,
                estimated_cost_saved_usd=0.001 if target != "cloud" else 0.0,
                mock_execution=True,
                prompt_preview=f"Test prompt number {i} with enough text",
            )
        )
        time.sleep(0.001)


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "routing.db"
    _seed_db(db_path, n=5)
    return TestClient(create_app(db_path))


def test_summary_returns_expected_shape(api_client: TestClient) -> None:
    response = api_client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["total_requests"] == 5
    assert set(data["by_target"].keys()) == {"small_local", "large_local", "cloud"}
    for target in data["by_target"].values():
        assert "count" in target
        assert "pct" in target
        assert "avg_latency_ms" in target

    cost = data["cost"]
    assert "savings_pct" in cost
    assert "savings_usd" in cost
    assert "per_1000_savings_usd" in cost
    assert cost["total_always_cloud_usd"] > cost["total_router_cloud_usd"]


def test_decisions_paginates_correctly(api_client: TestClient) -> None:
    page1 = api_client.get("/api/decisions?limit=2&offset=0")
    assert page1.status_code == 200
    data1 = page1.json()
    assert data1["total"] == 5
    assert data1["limit"] == 2
    assert data1["offset"] == 0
    assert len(data1["decisions"]) == 2

    page2 = api_client.get("/api/decisions?limit=2&offset=2")
    data2 = page2.json()
    assert len(data2["decisions"]) == 2
    assert data1["decisions"][0]["request_id"] != data2["decisions"][0]["request_id"]

    page3 = api_client.get("/api/decisions?limit=2&offset=4")
    data3 = page3.json()
    assert len(data3["decisions"]) == 1

    decision = data1["decisions"][0]
    assert {"timestamp", "prompt", "target", "reason", "complexity_score", "sensitivity_flag", "latency_ms"} <= decision.keys()


def test_decisions_filter_by_target(api_client: TestClient) -> None:
    response = api_client.get("/api/decisions?target=cloud")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(row["target"] == "cloud" for row in data["decisions"])


def test_index_serves_dashboard_html(api_client: TestClient) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    assert "Adaptive Router" in response.text
