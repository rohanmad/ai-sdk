"""Shared cloud cost estimation for routing analysis and telemetry dashboard."""

from __future__ import annotations

from typing import Any

# OpenAI gpt-4o-mini standard API pricing (Aug 2026).
# Source: https://developers.openai.com/api/docs/pricing
INPUT_PRICE_PER_1M = 0.15  # USD
OUTPUT_PRICE_PER_1M = 0.60  # USD

# Average completion length for cost estimate (collection used max_tokens=64).
DEFAULT_AVG_OUTPUT_TOKENS = 50

TARGETS = ("small_local", "large_local", "cloud")


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars/token for English text."""
    return max(1, int(len(text) / 4))


def cloud_request_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * INPUT_PRICE_PER_1M + (
        output_tokens / 1_000_000
    ) * OUTPUT_PRICE_PER_1M


def compute_cost_savings(
    rows: list[dict[str, Any]],
    *,
    avg_output_tokens: int | None = None,
) -> dict[str, float]:
    """Compare always-cloud baseline vs actual router cloud usage.

    Each row should have: target, prompt_tokens, completion_tokens.
    """
    if not rows:
        return {
            "total_always_cloud_usd": 0.0,
            "total_router_cloud_usd": 0.0,
            "savings_usd": 0.0,
            "savings_pct": 0.0,
            "per_1000_always_cloud_usd": 0.0,
            "per_1000_router_usd": 0.0,
            "per_1000_savings_usd": 0.0,
        }

    n = len(rows)
    total_always = 0.0
    total_router = 0.0

    for row in rows:
        prompt_tokens = int(row.get("prompt_tokens") or 0)
        completion_tokens = int(row.get("completion_tokens") or 0)
        if avg_output_tokens is not None and completion_tokens == 0:
            completion_tokens = avg_output_tokens

        request_cost = cloud_request_cost_usd(prompt_tokens, completion_tokens)
        total_always += request_cost
        if row.get("target") == "cloud":
            total_router += request_cost

    savings = total_always - total_router
    savings_pct = (savings / total_always * 100) if total_always else 0.0
    per_1000_always = (total_always / n) * 1000
    per_1000_router = (total_router / n) * 1000

    return {
        "total_always_cloud_usd": total_always,
        "total_router_cloud_usd": total_router,
        "savings_usd": savings,
        "savings_pct": savings_pct,
        "per_1000_always_cloud_usd": per_1000_always,
        "per_1000_router_usd": per_1000_router,
        "per_1000_savings_usd": per_1000_always - per_1000_router,
    }
