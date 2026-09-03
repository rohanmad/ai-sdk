"""Tests for offline quality metrics."""

from telemetry.quality import load_eval_quality_metrics


def test_load_eval_quality_metrics_from_csv() -> None:
    metrics = load_eval_quality_metrics()
    assert metrics["available"] is True
    assert metrics["eval_count"] == 300
    assert metrics["misroute_pct"] is not None
    assert 0 <= metrics["misroute_pct"] <= 100
    assert len(metrics["confidence_buckets"]) == 3
    assert metrics["avg_confidence"] is not None
