#!/usr/bin/env python3
"""Relabel existing prompts with improved labeling logic (no new prompts)."""

from __future__ import annotations

import argparse
import csv
import gc
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.complexity_classifier.collect_data import (  # noqa: E402
    DEFAULT_POLICY,
    DEFAULT_PROMPTS,
    FIELDNAMES,
    format_instruct_prompt,
    load_policy_model_paths,
    load_prompts,
    default_thread_count,
)
from packages.complexity_classifier.labeling import (  # noqa: E402
    DEFAULT_SIMILARITY_THRESHOLD,
    format_notes,
    label_outputs,
)
from packages.complexity_classifier.collect_data import load_encoder  # noqa: E402
from packages.execution.local_runner import LocalRunner, LocalRunnerConfig  # noqa: E402

DEFAULT_OUTPUT = ROOT / "data" / "labeled_requests.csv"
DEFAULT_BACKUP = ROOT / "data" / "labeled_requests_v1_backup.csv"
DEFAULT_CHANGES = ROOT / "data" / "label_changes.csv"


def load_old_labels(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=FIELDNAMES)
    return pd.read_csv(path)


def relabel(
    prompts_path: Path,
    output_path: Path,
    policy_path: Path,
    *,
    max_tokens: int = 64,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    n_threads: int | None = None,
    only_relabel_false: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    small_path, large_path = load_policy_model_paths(policy_path)
    prompts = load_prompts(prompts_path)
    old_df = load_old_labels(output_path)
    old_by_prompt = {
        str(row["prompt"]): row for _, row in old_df.iterrows()
    } if not old_df.empty else {}

    thread_count = n_threads if n_threads is not None else default_thread_count()
    runner: LocalRunner | None = None
    encoder = None

    new_rows: list[dict] = []
    total = len(prompts)
    for i, prompt in enumerate(prompts, start=1):
        old = old_by_prompt.get(prompt)
        old_val = str(old.get("small_sufficient", "")).strip().lower() if old is not None else ""

        if only_relabel_false and old_val == "true" and old is not None:
            new_rows.append(
                {
                    "prompt": prompt,
                    "complexity_label": old.get("complexity_label", "low"),
                    "small_sufficient": old_val,
                    "large_sufficient": str(old.get("large_sufficient", "true")).lower(),
                    "notes": old.get("notes", ""),
                }
            )
            print(f"[{i}/{total}] keep existing True label", flush=True)
            continue

        if runner is None:
            runner = LocalRunner(
                LocalRunnerConfig(
                    small_model_path=small_path,
                    large_model_path=large_path,
                    n_ctx=512,
                    n_threads=thread_count,
                )
            )
        if encoder is None:
            print("Loading embedding model...", flush=True)
            encoder = load_encoder()

        formatted = format_instruct_prompt(prompt)
        print(f"[{i}/{total}] small model...", flush=True)
        small_out = runner.generate(
            formatted, tier="small", max_tokens=max_tokens, temperature=0.1
        )
        if small_out.mock:
            raise RuntimeError("Small model fell back to mock mode")
        runner.unload("small")

        print(f"[{i}/{total}] large model...", flush=True)
        large_out = runner.generate(
            formatted, tier="large", max_tokens=max_tokens, temperature=0.1
        )
        if large_out.mock:
            raise RuntimeError("Large model fell back to mock mode")
        runner.unload("large")

        result = label_outputs(
            small_out.text,
            large_out.text,
            encoder,
            similarity_threshold=similarity_threshold,
        )
        new_rows.append(
            {
                "prompt": prompt,
                "complexity_label": result.complexity_label,
                "small_sufficient": str(result.small_sufficient).lower(),
                "large_sufficient": "true",
                "notes": format_notes(result),
            }
        )
        print(
            f"  sim={result.cosine_sim:.4f} sufficient={result.small_sufficient} "
            f"method={result.method}",
            flush=True,
        )

    if runner is not None:
        runner.unload()
    gc.collect()

    new_df = pd.DataFrame(new_rows)
    changes: list[dict] = []
    for row in new_rows:
        prompt = row["prompt"]
        old = old_by_prompt.get(prompt)
        if old is None:
            continue
        old_val = str(old.get("small_sufficient", "")).strip().lower()
        new_val = row["small_sufficient"]
        if old_val != new_val:
            changes.append(
                {
                    "prompt": prompt,
                    "old_small_sufficient": old_val,
                    "new_small_sufficient": new_val,
                    "old_notes": old.get("notes", ""),
                    "new_notes": row["notes"],
                }
            )

    changes_df = pd.DataFrame(changes)
    return new_df, changes_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel existing prompts")
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backup", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--changes", type=Path, default=DEFAULT_CHANGES)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Re-run models for all prompts (default: only old False labels)",
    )
    args = parser.parse_args()

    if args.output.exists():
        shutil.copy2(args.output, args.backup)
        print(f"Backed up old labels to {args.backup}", flush=True)

    new_df, changes_df = relabel(
        args.prompts,
        args.output,
        args.policy,
        max_tokens=args.max_tokens,
        similarity_threshold=args.similarity_threshold,
        n_threads=args.threads,
        only_relabel_false=not args.full,
    )

    new_df.to_csv(args.output, index=False, quoting=csv.QUOTE_ALL)
    if not changes_df.empty:
        changes_df.to_csv(args.changes, index=False, quoting=csv.QUOTE_ALL)

    true_count = (new_df["small_sufficient"].str.lower() == "true").sum()
    false_count = len(new_df) - true_count
    print("\n" + "=" * 60)
    print("RELABELING COMPLETE")
    print("=" * 60)
    print(f"Total rows: {len(new_df)}")
    print(f"small_sufficient=True:  {true_count} ({true_count/len(new_df)*100:.1f}%)")
    print(f"small_sufficient=False: {false_count} ({false_count/len(new_df)*100:.1f}%)")
    print(f"Labels changed: {len(changes_df)}")
    if not changes_df.empty:
        print(f"\nChanged rows written to {args.changes}")
        print(changes_df.to_string(index=False))


if __name__ == "__main__":
    main()
