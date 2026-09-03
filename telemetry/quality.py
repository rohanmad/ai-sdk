"""Offline routing quality metrics for the telemetry dashboard."""

from __future__ import annotations

import csv
import re
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_CSV = PKG_ROOT / "data" / "routing_cost_analysis.csv"

_CONFIDENCE_RE = re.compile(r"confidence=([0-9.]+)")


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _parse_confidence(reason: str, complexity_score: float) -> float:
    match = _CONFIDENCE_RE.search(reason)
    if match:
        return float(match.group(1))
    return max(complexity_score, 1.0 - complexity_score)


def load_eval_quality_metrics(
    csv_path: Path | None = None,
) -> dict[str, object]:
    """Compute misroute rate and classifier confidence buckets from eval CSV."""
    source = csv_path or DEFAULT_EVAL_CSV
    if not source.exists():
        return {
            "available": False,
            "source": str(source.name),
            "eval_count": 0,
            "misroute_pct": None,
            "misroute_count": 0,
            "confidence_buckets": [],
            "avg_confidence": None,
        }

    rows: list[dict[str, str]] = []
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        return {
            "available": False,
            "source": str(source.name),
            "eval_count": 0,
            "misroute_pct": None,
            "misroute_count": 0,
            "confidence_buckets": [],
            "avg_confidence": None,
        }

    misroute_count = 0
    confidences: list[float] = []
    bucket_counts = {"low": 0, "medium": 0, "high": 0}

    for row in rows:
        hard = _parse_bool(row.get("ground_truth_hard", "False"))
        target = row.get("target", "")
        if hard and target == "small_local":
            misroute_count += 1

        score = float(row.get("complexity_score") or 0.0)
        confidence = _parse_confidence(row.get("reason", ""), score)
        confidences.append(confidence)
        if confidence < 0.6:
            bucket_counts["low"] += 1
        elif confidence < 0.8:
            bucket_counts["medium"] += 1
        else:
            bucket_counts["high"] += 1

    total = len(rows)
    buckets = [
        {
            "label": "high",
            "range": "≥ 0.80",
            "count": bucket_counts["high"],
            "pct": round(bucket_counts["high"] / total * 100, 1),
        },
        {
            "label": "medium",
            "range": "0.60–0.79",
            "count": bucket_counts["medium"],
            "pct": round(bucket_counts["medium"] / total * 100, 1),
        },
        {
            "label": "low",
            "range": "< 0.60",
            "count": bucket_counts["low"],
            "pct": round(bucket_counts["low"] / total * 100, 1),
        },
    ]

    return {
        "available": True,
        "source": str(source.name),
        "eval_count": total,
        "misroute_pct": round(misroute_count / total * 100, 1),
        "misroute_count": misroute_count,
        "confidence_buckets": buckets,
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
    }
