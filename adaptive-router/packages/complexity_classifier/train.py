"""Trains the complexity classifier on labeled request data (step 5)."""

from __future__ import annotations

import argparse
from pathlib import Path


def train(data_path: Path, output_path: Path) -> None:
    """Train logistic regression / XGBoost on labeled_requests.csv."""
    raise NotImplementedError(
        "Collect labeled data (build step 4) before training. "
        f"Expected data at {data_path}, output at {output_path}."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train complexity classifier")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/labeled_requests.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("packages/complexity-classifier/model.pkl"),
    )
    args = parser.parse_args()
    train(args.data, args.output)
