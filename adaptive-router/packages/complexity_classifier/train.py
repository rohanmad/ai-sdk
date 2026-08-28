"""Train complexity classifier from labeled_requests.csv."""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

from packages.complexity_classifier.vectorize import prompt_to_array

DEFAULT_DATA = Path("data/labeled_requests.csv")
DEFAULT_OUTPUT = Path("packages/complexity_classifier/model.pkl")

CLASS_LABELS = [False, True]  # small_sufficient=False (high complexity) first


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


def build_feature_matrix(prompts: list[str]) -> np.ndarray:
    rows = [prompt_to_array(prompt) for prompt in prompts]
    return np.vstack(rows)


def print_class_distribution(y: np.ndarray, label: str) -> dict[bool, int]:
    series = pd.Series(y, name="small_sufficient")
    counts = series.value_counts().to_dict()
    print(f"\n{label}:")
    for cls in CLASS_LABELS:
        count = counts.get(cls, 0)
        pct = count / len(y) * 100 if len(y) else 0.0
        print(f"  small_sufficient={cls}: {count} ({pct:.1f}%)")
    return counts


def format_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> str:
    cm = confusion_matrix(y_true, y_pred, labels=CLASS_LABELS)
    lines = [
        "Confusion matrix (rows=actual, cols=predicted):",
        "                      pred=False  pred=True",
        f"  actual=False (hard):      {cm[0, 0]:6d}      {cm[0, 1]:6d}",
        f"  actual=True  (easy):      {cm[1, 0]:6d}      {cm[1, 1]:6d}",
        "",
        "  TN={tn}  FP={fp}  FN={fn}  TP={tp}".format(
            tn=cm[0, 0], fp=cm[0, 1], fn=cm[1, 0], tp=cm[1, 1]
        ),
    ]
    return "\n".join(lines)


def per_class_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASS_LABELS, zero_division=0
    )
    return {
        "False": {
            "precision": float(precision[0]),
            "recall": float(recall[0]),
            "f1": float(f1[0]),
            "support": int(support[0]),
        },
        "True": {
            "precision": float(precision[1]),
            "recall": float(recall[1]),
            "f1": float(f1[1]),
            "support": int(support[1]),
        },
    }


def is_degenerate(y_pred: np.ndarray) -> bool:
    """True if model predicts essentially one class only."""
    unique, counts = np.unique(y_pred, return_counts=True)
    if len(unique) <= 1:
        return True
    majority_frac = counts.max() / len(y_pred)
    return majority_frac >= 0.95


def train(
    data_path: Path,
    output_path: Path,
    random_state: int = 42,
    *,
    class_weight: str | dict | None = "balanced",
) -> dict:
    df, _ = load_dataset(data_path)
    X = build_feature_matrix(df["prompt"].tolist())
    y = df["small_sufficient"].astype(bool).values

    print("=" * 60)
    print("STEP 1 — CLASS DISTRIBUTION DIAGNOSIS")
    print("=" * 60)
    print_class_distribution(y, "Full dataset")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )
    print_class_distribution(y_train, "Train split (80%)")
    print_class_distribution(y_test, "Test split (20%)")

    had_class_weight = class_weight is not None
    print(f"\nLogisticRegression class_weight={class_weight!r}")

    model = LogisticRegression(
        max_iter=1000,
        random_state=random_state,
        class_weight=class_weight,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    by_class = per_class_metrics(y_test, y_pred)
    degenerate = is_degenerate(y_pred)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    return {
        "accuracy": float(accuracy),
        "by_class": by_class,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=CLASS_LABELS).tolist(),
        "confusion_matrix_text": format_confusion_matrix(y_test, y_pred),
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "class_weight": class_weight,
        "had_class_weight": had_class_weight,
        "degenerate": degenerate,
        "report": classification_report(
            y_test, y_pred, labels=CLASS_LABELS, zero_division=0
        ),
        "y_pred": y_pred,
        "y_test": y_test,
    }


def print_metrics(metrics: dict) -> None:
    print("\n" + "=" * 60)
    print("HELD-OUT METRICS (80/20 split)")
    print("=" * 60)
    print(f"Overall accuracy: {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print()
    print(metrics["confusion_matrix_text"])
    print()
    print("Per-class metrics:")
    for cls_name, label in [("False", "small_sufficient=False (high complexity)"),
                            ("True", "small_sufficient=True (low complexity)")]:
        m = metrics["by_class"][cls_name]
        print(
            f"  {label}:"
            f" precision={m['precision']:.4f}"
            f" recall={m['recall']:.4f}"
            f" f1={m['f1']:.4f}"
            f" (support={m['support']})"
        )
    print()
    if metrics["degenerate"]:
        print("WARNING: Model is DEGENERATE — predicts one class ≥95% of the time.")
    else:
        print("Model is NOT degenerate — predicts both classes on held-out set.")
    print("-" * 60)
    print(metrics["report"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train complexity classifier")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--no-balanced",
        action="store_true",
        help="Disable class_weight='balanced' (reproduce old behavior)",
    )
    args = parser.parse_args()

    class_weight = None if args.no_balanced else "balanced"
    metrics = train(
        args.data, args.output, random_state=args.random_state, class_weight=class_weight
    )
    print_metrics(metrics)
    print(f"\nModel saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
