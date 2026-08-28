#!/usr/bin/env python3
"""Run full router pipeline on labeled prompts and estimate cloud cost savings."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.complexity_classifier.predict import _load_model  # noqa: E402
from packages.routing_engine.decide import DecideInput, PolicyConfig, decide  # noqa: E402
from packages.sensitivity_gate.rules import check_sensitivity  # noqa: E402
from telemetry.cost import (  # noqa: E402
    DEFAULT_AVG_OUTPUT_TOKENS,
    INPUT_PRICE_PER_1M,
    OUTPUT_PRICE_PER_1M,
    cloud_request_cost_usd,
    estimate_tokens,
)

DEFAULT_DATA = ROOT / "data" / "labeled_requests.csv"
DEFAULT_POLICY = ROOT / "config" / "policy.yaml"
DEFAULT_OUTPUT = ROOT / "data" / "routing_cost_analysis.csv"


def parse_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def analyze(
    data_path: Path,
    policy_path: Path,
    *,
    avg_output_tokens: int = DEFAULT_AVG_OUTPUT_TOKENS,
) -> tuple[pd.DataFrame, dict]:
    _load_model.cache_clear()
    model = _load_model(str((ROOT / "packages/complexity_classifier/model.pkl").resolve()))
    n_features = model.coef_.shape[1]
    if n_features != 6:
        raise ValueError(f"Expected 6-feature production model, got {n_features}")

    policy = PolicyConfig.load(policy_path)
    if policy.dumb_routing.get("enabled"):
        raise ValueError("Production policy must have dumb_routing.enabled=false")

    df = pd.read_csv(data_path)
    rows: list[dict] = []

    for _, record in df.iterrows():
        prompt = str(record["prompt"])
        gt_hard = not parse_bool(record["small_sufficient"])

        sens = check_sensitivity(prompt)
        decision = decide(
            DecideInput(
                prompt=prompt,
                sensitivity_flag=sens.is_sensitive,
                sensitivity_triggers=sens.triggers,
                complexity_score=0.0,
            ),
            policy,
        )

        input_tokens = estimate_tokens(prompt)
        rows.append(
            {
                "prompt": prompt,
                "ground_truth_hard": gt_hard,
                "sensitivity_flag": sens.is_sensitive,
                "target": decision.target,
                "reason": decision.reason,
                "complexity_level": decision.complexity_level,
                "complexity_score": decision.complexity_score,
                "input_tokens_est": input_tokens,
            }
        )

    result = pd.DataFrame(rows)
    n = len(result)

    target_counts = result["target"].value_counts()
    target_pct = (target_counts / n * 100).to_dict()

    cloud_mask = result["target"] == "cloud"
    n_cloud = int(cloud_mask.sum())

    hard_mask = result["ground_truth_hard"]
    routed_small = result["target"] == "small_local"
    false_negative_to_small = int((hard_mask & routed_small).sum())
    fn_pct_of_eval = false_negative_to_small / n * 100
    fn_pct_of_hard = (
        false_negative_to_small / int(hard_mask.sum()) * 100 if hard_mask.any() else 0.0
    )

    avg_input = result["input_tokens_est"].mean()
    per_request_always_cloud = cloud_request_cost_usd(int(avg_input), avg_output_tokens)
    total_always_cloud = per_request_always_cloud * n

    cloud_input_tokens = result.loc[cloud_mask, "input_tokens_est"].sum()
    total_router_cloud = cloud_request_cost_usd(int(cloud_input_tokens), avg_output_tokens * n_cloud)

    savings_usd = total_always_cloud - total_router_cloud
    savings_pct = savings_usd / total_always_cloud * 100 if total_always_cloud else 0.0
    per_1000_always = per_request_always_cloud * 1000
    per_1000_router = (total_router_cloud / n) * 1000
    per_1000_savings = per_1000_always - per_1000_router

    summary = {
        "n_prompts": n,
        "n_hard_ground_truth": int(hard_mask.sum()),
        "model_features": n_features,
        "target_counts": target_counts.to_dict(),
        "target_pct": target_pct,
        "n_cloud": n_cloud,
        "n_sensitive": int(result["sensitivity_flag"].sum()),
        "false_negative_to_small": false_negative_to_small,
        "false_negative_pct_of_eval": fn_pct_of_eval,
        "false_negative_pct_of_hard": fn_pct_of_hard,
        "avg_input_tokens_est": float(avg_input),
        "avg_output_tokens_assumed": avg_output_tokens,
        "input_price_per_1m": INPUT_PRICE_PER_1M,
        "output_price_per_1m": OUTPUT_PRICE_PER_1M,
        "per_request_always_cloud_usd": per_request_always_cloud,
        "total_always_cloud_usd": total_always_cloud,
        "total_router_cloud_usd": total_router_cloud,
        "savings_usd": savings_usd,
        "savings_pct": savings_pct,
        "per_1000_always_cloud_usd": per_1000_always,
        "per_1000_router_usd": per_1000_router,
        "per_1000_savings_usd": per_1000_savings,
    }
    return result, summary


def print_report(summary: dict) -> None:
    print("=" * 60)
    print("ROUTING DISTRIBUTION (n={})".format(summary["n_prompts"]))
    print("=" * 60)
    for target in ("small_local", "large_local", "cloud"):
        count = summary["target_counts"].get(target, 0)
        pct = summary["target_pct"].get(target, 0.0)
        print(f"  {target:12} {count:4d}  ({pct:5.1f}%)")
    print(f"\nSensitive prompts (PII regex): {summary['n_sensitive']}")

    print("\n" + "=" * 60)
    print("ERROR COST (hard prompts routed to small_local)")
    print("=" * 60)
    print(
        f"  False negatives → small_local: {summary['false_negative_to_small']} / "
        f"{summary['n_prompts']} eval prompts "
        f"({summary['false_negative_pct_of_eval']:.1f}%)"
    )
    print(
        f"  Of ground-truth hard prompts ({summary['n_hard_ground_truth']}): "
        f"{summary['false_negative_pct_of_hard']:.1f}% sent to small_local"
    )

    print("\n" + "=" * 60)
    print("COST ASSUMPTIONS")
    print("=" * 60)
    print("  Cloud model: gpt-4o-mini (per config/policy.yaml)")
    print("  Pricing: $0.15 / 1M input tokens, $0.60 / 1M output tokens")
    print("  Source: https://developers.openai.com/api/docs/pricing")
    print("  Local inference (small_local, large_local): $0 API cost (hardware ignored)")
    print(f"  Avg input tokens/prompt (est.): {summary['avg_input_tokens_est']:.1f}")
    print(f"  Avg output tokens/request (assumed): {summary['avg_output_tokens_assumed']}")

    print("\n" + "=" * 60)
    print("COST COMPARISON")
    print("=" * 60)
    print(f"  Per-request (always cloud):     ${summary['per_request_always_cloud_usd']:.6f}")
    print(f"  Total always-cloud ({summary['n_prompts']} req): ${summary['total_always_cloud_usd']:.4f}")
    print(
        f"  Total router (cloud only, {summary['n_cloud']} req): "
        f"${summary['total_router_cloud_usd']:.4f}"
    )
    print(f"  Savings: ${summary['savings_usd']:.4f} ({summary['savings_pct']:.1f}%)")
    print(f"  Per 1,000 requests — always cloud: ${summary['per_1000_always_cloud_usd']:.2f}")
    print(f"  Per 1,000 requests — router:       ${summary['per_1000_router_usd']:.2f}")
    print(f"  Per 1,000 requests — savings:    ${summary['per_1000_savings_usd']:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze routing distribution and cost")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--avg-output-tokens", type=int, default=DEFAULT_AVG_OUTPUT_TOKENS)
    args = parser.parse_args()

    result, summary = analyze(
        args.data,
        args.policy,
        avg_output_tokens=args.avg_output_tokens,
    )
    result.to_csv(args.output, index=False, quoting=csv.QUOTE_ALL)
    print_report(summary)
    print(f"\nPer-prompt routing written to {args.output}")


if __name__ == "__main__":
    main()
