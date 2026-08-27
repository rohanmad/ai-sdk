"""Collect labeled training data by comparing small vs large local model outputs."""

from __future__ import annotations

import argparse
import csv
import gc
import os
import sys
from pathlib import Path

import yaml
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.execution.local_runner import LocalRunner, LocalRunnerConfig  # noqa: E402

DEFAULT_PROMPTS = ROOT / "data" / "sample_prompts.txt"
DEFAULT_OUTPUT = ROOT / "data" / "labeled_requests.csv"
DEFAULT_POLICY = ROOT / "config" / "policy.yaml"
SIMILARITY_THRESHOLD = 0.85
ENCODER_NAME = "sentence-transformers/all-MiniLM-L6-v2"

FIELDNAMES = [
    "prompt",
    "complexity_label",
    "small_sufficient",
    "large_sufficient",
    "notes",
]


def load_policy_model_paths(policy_path: Path) -> tuple[str, str]:
    with open(policy_path, encoding="utf-8") as f:
        policy = yaml.safe_load(f)
    models = policy.get("models", {})
    small = models.get("small_local", {}).get("path", "")
    large = models.get("large_local", {}).get("path", "")
    if not small or not large:
        raise ValueError(
            f"Both small_local.path and large_local.path must be set in {policy_path}"
        )
    return small, large


def load_prompts(path: Path) -> list[str]:
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return lines


def format_instruct_prompt(prompt: str) -> str:
    return (
        f"<|im_start|>user\n{prompt}\n"
        f"<|im_start|>assistant\n"
    )


def load_encoder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(ENCODER_NAME)


def cosine_sim(a: str, b: str, encoder) -> float:
    embeddings = encoder.encode([a, b])
    return float(cosine_similarity([embeddings[0]], [embeddings[1]])[0, 0])


def append_row(output_path: Path, row: dict) -> None:
    write_header = not output_path.exists() or output_path.stat().st_size == 0
    with open(output_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def default_thread_count() -> int:
    cpus = os.cpu_count() or 4
    return max(2, min(4, cpus // 2))


def collect(
    prompts_path: Path,
    output_path: Path,
    policy_path: Path,
    *,
    max_tokens: int = 64,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    skip_existing: bool = True,
    limit: int | None = None,
    max_new: int | None = None,
    n_threads: int | None = None,
) -> int:
    small_path, large_path = load_policy_model_paths(policy_path)
    prompts = load_prompts(prompts_path)
    if limit is not None:
        prompts = prompts[:limit]

    existing: set[str] = set()
    if skip_existing and output_path.exists():
        import pandas as pd

        df = pd.read_csv(output_path)
        if "prompt" in df.columns and not df.empty:
            existing = set(df["prompt"].astype(str).tolist())

    thread_count = n_threads if n_threads is not None else default_thread_count()
    runner = LocalRunner(
        LocalRunnerConfig(
            small_model_path=small_path,
            large_model_path=large_path,
            n_ctx=512,
            n_threads=thread_count,
        )
    )
    encoder = None

    collected = 0
    total = len(prompts)
    for i, prompt in enumerate(prompts, start=1):
        if prompt in existing:
            print(f"[{i}/{total}] skip existing", flush=True)
            continue

        formatted = format_instruct_prompt(prompt)
        print(f"[{i}/{total}] running small model...", flush=True)
        small_out = runner.generate(
            formatted, tier="small", max_tokens=max_tokens, temperature=0.1
        )
        if small_out.mock:
            raise RuntimeError("Small model fell back to mock mode — check model path")
        runner.unload("small")

        print(f"[{i}/{total}] running large model...", flush=True)
        large_out = runner.generate(
            formatted, tier="large", max_tokens=max_tokens, temperature=0.1
        )
        if large_out.mock:
            raise RuntimeError("Large model fell back to mock mode — check model path")
        runner.unload("large")

        if encoder is None:
            print(f"[{i}/{total}] loading embedding model...", flush=True)
            encoder = load_encoder()

        sim = cosine_sim(small_out.text, large_out.text, encoder)
        small_sufficient = sim >= similarity_threshold
        complexity_label = "low" if small_sufficient else "high"

        row = {
            "prompt": prompt,
            "complexity_label": complexity_label,
            "small_sufficient": str(small_sufficient).lower(),
            "large_sufficient": "true",
            "notes": f"cosine_sim={sim:.4f}",
        }
        append_row(output_path, row)
        collected += 1
        print(
            f"  sim={sim:.4f} small_sufficient={small_sufficient} "
            f"({small_out.latency_ms:.0f}ms + {large_out.latency_ms:.0f}ms)",
            flush=True,
        )
        if max_new is not None and collected >= max_new:
            print(f"Reached --max-new {max_new}, stopping batch.", flush=True)
            break

    runner.unload()
    gc.collect()
    return collected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect labeled complexity data (memory-safe: one model at a time)"
    )
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--similarity-threshold", type=float, default=SIMILARITY_THRESHOLD)
    parser.add_argument("--limit", type=int, default=None, help="Max prompts to process")
    parser.add_argument(
        "--max-new",
        type=int,
        default=None,
        help="Stop after collecting this many new rows (for batch runs)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="llama.cpp thread count (default: capped at 4 for laptop safety)",
    )
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    print(
        f"Collecting up to {args.limit or 'all'} prompts "
        f"(threads={args.threads or default_thread_count()}, max_tokens={args.max_tokens})",
        flush=True,
    )
    count = collect(
        args.prompts,
        args.output,
        args.policy,
        max_tokens=args.max_tokens,
        similarity_threshold=args.similarity_threshold,
        skip_existing=not args.no_skip_existing,
        limit=args.limit,
        max_new=args.max_new,
        n_threads=args.threads,
    )
    print(f"Appended {count} labeled rows to {args.output}", flush=True)


if __name__ == "__main__":
    main()
