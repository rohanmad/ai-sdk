#!/usr/bin/env python3
"""Surface disputed factual rows among remaining small_sufficient=False labels."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.complexity_classifier.collect_data import (  # noqa: E402
    DEFAULT_POLICY,
    format_instruct_prompt,
    load_encoder,
    load_policy_model_paths,
    default_thread_count,
)
from packages.complexity_classifier.labeling import (  # noqa: E402
    DEFAULT_SHORT_OUTPUT_WORDS,
    cosine_sim,
    label_outputs,
    substring_answer_match,
    word_count,
)
from packages.execution.local_runner import LocalRunner, LocalRunnerConfig  # noqa: E402

DEFAULT_DATA = ROOT / "data" / "labeled_requests.csv"

_OPEN_ENDED_STARTERS = (
    "design ",
    "debug ",
    "analyze ",
    "compare ",
    "propose ",
    "plan ",
    "trace ",
    "given ",
    "a user reports",
)


def is_plausibly_simple_factual(prompt: str) -> bool:
    """Heuristic: short factual Q&A, not design/debug/analyze style."""
    lowered = prompt.strip().lower()
    if any(lowered.startswith(s) for s in _OPEN_ENDED_STARTERS):
        return False
    words = word_count(prompt)
    if words > 14:
        return False
    if "step-by-step" in lowered or "tradeoff" in lowered:
        return False
    factual_patterns = (
        r"^what (is|are|does|color|organ|happens|year|gas)",
        r"^who (wrote|invented|discovered)",
        r"^how many ",
        r"^when (did|was|is)",
        r"^where (is|are)",
        r"^which (is|are)",
        r"^name ",
    )
    if any(re.search(p, lowered) for p in factual_patterns):
        return True
    if lowered.startswith("explain ") and words <= 10:
        return True
    return False


def inspect_row(
    prompt: str,
    runner: LocalRunner,
    encoder,
    *,
    max_tokens: int = 64,
) -> dict:
    formatted = format_instruct_prompt(prompt)
    small_out = runner.generate(formatted, tier="small", max_tokens=max_tokens, temperature=0.1)
    if small_out.mock:
        raise RuntimeError("Small model fell back to mock mode")
    runner.unload("small")

    large_out = runner.generate(formatted, tier="large", max_tokens=max_tokens, temperature=0.1)
    if large_out.mock:
        raise RuntimeError("Large model fell back to mock mode")
    runner.unload("large")

    result = label_outputs(small_out.text, large_out.text, encoder, prompt=prompt)
    return {
        "prompt": prompt,
        "small_output": small_out.text.strip(),
        "large_output": large_out.text.strip(),
        "cosine_sim": result.cosine_sim,
        "method": result.method,
        "short_output": result.short_output,
        "substring_match": result.substring_match,
        "small_words": word_count(small_out.text),
        "large_words": word_count(large_out.text),
        "plausibly_factual": is_plausibly_simple_factual(prompt),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect disputed False labels")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument(
        "--factual-only",
        action="store_true",
        help="Only print plausibly simple factual prompts",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    false_df = df[df["small_sufficient"].astype(str).str.lower() == "false"]
    print(f"Total False rows: {len(false_df)}\n")

    small_path, large_path = load_policy_model_paths(args.policy)
    thread_count = args.threads if args.threads is not None else default_thread_count()
    runner = LocalRunner(
        LocalRunnerConfig(
            small_model_path=small_path,
            large_model_path=large_path,
            n_ctx=512,
            n_threads=thread_count,
        )
    )
    print("Loading embedding model...", flush=True)
    encoder = load_encoder()

    rows: list[dict] = []
    for i, prompt in enumerate(false_df["prompt"].astype(str), start=1):
        print(f"[{i}/{len(false_df)}] {prompt[:60]}...", flush=True)
        rows.append(inspect_row(prompt, runner, encoder, max_tokens=args.max_tokens))

    runner.unload()

    disputed = [
        r
        for r in rows
        if r["plausibly_factual"]
        and not r["substring_match"]
        and (
            r["short_output"]
            or word_count(r["prompt"]) <= DEFAULT_SHORT_OUTPUT_WORDS
        )
    ]

    # Also include factual prompts where substring wasn't evaluated (verbose outputs)
    factual_no_match = [
        r for r in rows if r["plausibly_factual"] and not r["substring_match"]
    ]

    target = disputed if args.factual_only else factual_no_match
    print("\n" + "=" * 72)
    print(f"DISPUTED FACTUAL ROWS (n={len(target)})")
    print("=" * 72)

    for i, r in enumerate(target, start=1):
        print(f"\n--- [{i}] ---")
        print(f"PROMPT:       {r['prompt']}")
        print(f"SMALL OUTPUT: {r['small_output']!r}")
        print(f"LARGE OUTPUT: {r['large_output']!r}")
        print(
            f"cosine_sim={r['cosine_sim']:.4f}  method={r['method']}  "
            f"short_output={r['short_output']}  substring_match={r['substring_match']}  "
            f"(small_words={r['small_words']}, large_words={r['large_words']})"
        )

    open_ended = [r for r in rows if not r["plausibly_factual"]]
    print("\n" + "=" * 72)
    print(f"OPEN-ENDED FALSE ROWS (n={len(open_ended)}) — listed for reference")
    print("=" * 72)
    for r in open_ended:
        print(f"  - {r['prompt'][:70]}")


if __name__ == "__main__":
    main()
