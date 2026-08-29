#!/usr/bin/env python3
"""Relabel specific prompts and merge back into labeled_requests.csv."""

from __future__ import annotations

import argparse
import csv
import gc
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.complexity_classifier.collect_data import (  # noqa: E402
    DEFAULT_POLICY,
    FIELDNAMES,
    format_instruct_prompt,
    load_encoder,
    load_policy_model_paths,
    default_thread_count,
)
from packages.complexity_classifier.labeling import (  # noqa: E402
    DEFAULT_SIMILARITY_THRESHOLD,
    format_notes,
    label_outputs,
)
from packages.execution.local_runner import LocalRunner, LocalRunnerConfig  # noqa: E402

DEFAULT_DATA = ROOT / "data" / "labeled_requests.csv"
DEFAULT_BACKUP = ROOT / "data" / "labeled_requests_v2_backup.csv"
DEFAULT_CHANGES = ROOT / "data" / "label_changes_v2.csv"


def relabel_prompts(
    prompts: list[str],
    data_path: Path,
    policy_path: Path,
    *,
    max_tokens: int = 64,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    n_threads: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(data_path)
    old_by_prompt = {str(row["prompt"]): row for _, row in df.iterrows()}

    small_path, large_path = load_policy_model_paths(policy_path)
    thread_count = n_threads if n_threads is not None else default_thread_count()
    runner = LocalRunner(
        LocalRunnerConfig(
            small_model_path=small_path,
            large_model_path=large_path,
            n_ctx=512,
            n_threads=thread_count,
        )
    )
    encoder = load_encoder()

    changes: list[dict] = []
    for i, prompt in enumerate(prompts, start=1):
        print(f"[{i}/{len(prompts)}] {prompt}", flush=True)
        formatted = format_instruct_prompt(prompt)
        small_out = runner.generate(formatted, tier="small", max_tokens=max_tokens, temperature=0.1)
        if small_out.mock:
            raise RuntimeError("Small model fell back to mock mode")
        runner.unload("small")

        large_out = runner.generate(formatted, tier="large", max_tokens=max_tokens, temperature=0.1)
        if large_out.mock:
            raise RuntimeError("Large model fell back to mock mode")
        runner.unload("large")

        result = label_outputs(
            small_out.text,
            large_out.text,
            encoder,
            prompt=prompt,
            similarity_threshold=similarity_threshold,
        )
        new_row = {
            "prompt": prompt,
            "complexity_label": result.complexity_label,
            "small_sufficient": str(result.small_sufficient).lower(),
            "large_sufficient": "true",
            "notes": format_notes(result),
        }
        old = old_by_prompt.get(prompt)
        old_val = str(old.get("small_sufficient", "")).strip().lower() if old is not None else ""
        if old_val != new_row["small_sufficient"]:
            changes.append(
                {
                    "prompt": prompt,
                    "old_small_sufficient": old_val,
                    "new_small_sufficient": new_row["small_sufficient"],
                    "old_notes": old.get("notes", "") if old is not None else "",
                    "new_notes": new_row["notes"],
                }
            )
        df.loc[df["prompt"] == prompt, FIELDNAMES] = list(new_row.values())
        print(
            f"  sufficient={result.small_sufficient} method={result.method}",
            flush=True,
        )

    runner.unload()
    gc.collect()
    return df, pd.DataFrame(changes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel selected prompts in CSV")
    parser.add_argument("prompts", nargs="+", help="Prompt text(s) to relabel")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--backup", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--changes", type=Path, default=DEFAULT_CHANGES)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--threads", type=int, default=None)
    args = parser.parse_args()

    shutil.copy2(args.data, args.backup)
    print(f"Backed up to {args.backup}", flush=True)

    df, changes_df = relabel_prompts(
        args.prompts,
        args.data,
        args.policy,
        max_tokens=args.max_tokens,
        n_threads=args.threads,
    )
    df.to_csv(args.data, index=False, quoting=csv.QUOTE_ALL)
    if not changes_df.empty:
        changes_df.to_csv(args.changes, index=False, quoting=csv.QUOTE_ALL)

    true_count = (df["small_sufficient"].astype(str).str.lower() == "true").sum()
    false_count = len(df) - true_count
    print(f"\nTotal rows: {len(df)}")
    print(f"True: {true_count}  False: {false_count}")
    print(f"Changed: {len(changes_df)}")
    if not changes_df.empty:
        print(changes_df.to_string(index=False))


if __name__ == "__main__":
    main()
