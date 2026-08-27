"""Train complexity classifier from labeled_requests.csv."""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from packages.complexity_classifier.vectorize import prompt_to_array

DEFAULT_DATA = Path("data/labeled_requests.csv")
DEFAULT_OUTPUT = Path("packages/complexity_classifier/model.pkl")


def load_dataset(data_path: Path) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(data_path)
    required = {"prompt", "small_sufficient"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {data_path}: {missing}")
    df["small_sufficient"] = df["small_sufficient"].map(_parse_bool)
    df = df.dropna(subset=["prompt", "small_sufficient"])
    return df, list(df.columns)


def _parse_bool(value) -> bool | None:
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


def build_feature_matrix(prompts: list[str]):
    import numpy as np

    rows = [prompt_to_array(prompt) for prompt in prompts]
    return np.vstack(rows)


def train(data_path: Path, output_path: Path, random_state: int = 42) -> dict:
    df, _ = load_dataset(data_path)
    X = build_feature_matrix(df["prompt"].tolist())
    y = df["small_sufficient"].astype(bool).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    model = LogisticRegression(max_iter=1000, random_state=random_state)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", pos_label=True, zero_division=0
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "report": classification_report(y_test, y_pred, zero_division=0),
    }
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train complexity classifier")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    metrics = train(args.data, args.output, random_state=args.random_state)

    print("=" * 60)
    print("COMPLEXITY CLASSIFIER — HELD-OUT METRICS (80/20 split)")
    print("=" * 60)
    print(f"Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print(f"Precision: {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)")
    print(f"Recall:    {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)")
    print(f"F1:        {metrics['f1']:.4f}")
    print(f"Train size: {metrics['train_size']} | Test size: {metrics['test_size']}")
    print("-" * 60)
    print(metrics["report"])
    print(f"Model saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
