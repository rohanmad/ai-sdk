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
from sklearn.model_selection import StratifiedKFold, train_test_split

from packages.complexity_classifier.features import embed_prompts, extract_features
from packages.complexity_classifier.vectorize import (
    HANDCRAFTED_FEATURE_NAMES,
    LEGACY_HANDCRAFTED_DIM,
    prompts_to_matrix,
)

DEFAULT_DATA = Path("data/labeled_requests.csv")
DEFAULT_OUTPUT = Path("packages/complexity_classifier/model.pkl")

CLASS_LABELS = [False, True]  # small_sufficient=False (high complexity) first
METRIC_KEYS = ("accuracy", "precision", "recall", "f1")


def load_dataset(data_path: Path) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    required = {"prompt", "small_sufficient"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {data_path}: {missing}")
    df["small_sufficient"] = df["small_sufficient"].map(_parse_bool)
    return df.dropna(subset=["prompt", "small_sufficient"]).reset_index(drop=True)


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


def build_feature_matrix(prompts: list[str], *, use_embeddings: bool = True) -> np.ndarray:
    return prompts_to_matrix(prompts, use_embeddings=use_embeddings)


def make_model(random_state: int, class_weight: str | dict | None) -> LogisticRegression:
    return LogisticRegression(
        max_iter=1000,
        random_state=random_state,
        class_weight=class_weight,
    )


def print_class_distribution(y: np.ndarray, label: str) -> None:
    series = pd.Series(y, name="small_sufficient")
    counts = series.value_counts()
    print(f"\n{label}:")
    for cls in CLASS_LABELS:
        count = int(counts.get(cls, 0))
        pct = count / len(y) * 100 if len(y) else 0.0
        print(f"  small_sufficient={cls}: {count} ({pct:.1f}%)")


def format_confusion_matrix(cm: np.ndarray) -> str:
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
    accuracy = accuracy_score(y_true, y_pred)
    return {
        "accuracy": float(accuracy),
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
    unique, counts = np.unique(y_pred, return_counts=True)
    if len(unique) <= 1:
        return True
    return counts.max() / len(y_pred) >= 0.95


def out_of_fold_probabilities(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_splits: int,
    random_state: int,
    class_weight: str | dict | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return pooled out-of-fold true labels and P(small_sufficient=True)."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    oof_proba_true = np.zeros(len(y), dtype=np.float64)
    oof_y = np.zeros(len(y), dtype=bool)

    for train_idx, val_idx in skf.split(X, y):
        model = make_model(random_state, class_weight)
        model.fit(X[train_idx], y[train_idx])
        proba = model.predict_proba(X[val_idx])
        classes = list(model.classes_)
        idx_true = classes.index(True)
        oof_proba_true[val_idx] = proba[:, idx_true]
        oof_y[val_idx] = y[val_idx]

    return oof_y, oof_proba_true


def predict_from_threshold(proba_true: np.ndarray, threshold: float) -> np.ndarray:
    return proba_true >= threshold


def cross_validate(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_splits: int = 5,
    random_state: int = 42,
    class_weight: str | dict | None = "balanced",
    threshold: float = 0.5,
) -> dict:
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    fold_metrics: list[dict] = []
    aggregated_cm = np.zeros((2, 2), dtype=int)

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
        model = make_model(random_state, class_weight)
        model.fit(X[train_idx], y[train_idx])
        proba = model.predict_proba(X[val_idx])
        classes = list(model.classes_)
        idx_true = classes.index(True)
        y_pred = predict_from_threshold(proba[:, idx_true], threshold)

        fold_metrics.append(per_class_metrics(y[val_idx], y_pred))
        aggregated_cm += confusion_matrix(y[val_idx], y_pred, labels=CLASS_LABELS)

    def summarize(class_name: str) -> dict[str, tuple[float, float]]:
        result: dict[str, tuple[float, float]] = {}
        if class_name == "accuracy":
            vals = [m["accuracy"] for m in fold_metrics]
            result["accuracy"] = (float(np.mean(vals)), float(np.std(vals, ddof=0)))
            return result
        for metric in ("precision", "recall", "f1"):
            vals = [m[class_name][metric] for m in fold_metrics]
            result[metric] = (float(np.mean(vals)), float(np.std(vals, ddof=0)))
        return result

    return {
        "n_splits": n_splits,
        "threshold": threshold,
        "fold_metrics": fold_metrics,
        "aggregated_cm": aggregated_cm,
        "accuracy": summarize("accuracy")["accuracy"],
        "False": summarize("False"),
        "True": summarize("True"),
    }


def threshold_sweep_cv(
    X: np.ndarray,
    y: np.ndarray,
    *,
    n_splits: int = 5,
    random_state: int = 42,
    class_weight: str | dict | None = "balanced",
    thresholds: list[float] | None = None,
) -> list[dict]:
    if thresholds is None:
        thresholds = [round(t, 2) for t in np.arange(0.30, 0.71, 0.05)]

    oof_y, oof_proba_true = out_of_fold_probabilities(
        X, y, n_splits=n_splits, random_state=random_state, class_weight=class_weight
    )

    rows: list[dict] = []
    for threshold in thresholds:
        y_pred = predict_from_threshold(oof_proba_true, threshold)
        metrics = per_class_metrics(oof_y, y_pred)
        rows.append(
            {
                "threshold": threshold,
                "accuracy": metrics["accuracy"],
                "false_precision": metrics["False"]["precision"],
                "false_recall": metrics["False"]["recall"],
                "false_f1": metrics["False"]["f1"],
                "true_precision": metrics["True"]["precision"],
                "true_recall": metrics["True"]["recall"],
                "true_f1": metrics["True"]["f1"],
            }
        )
    return rows


def inspect_handcrafted_features(df: pd.DataFrame, random_state: int = 42) -> dict:
    false_df = df[~df["small_sufficient"]].copy()
    true_df = df[df["small_sufficient"]].copy()
    n_false = len(false_df)
    n_sample = min(n_false, len(true_df))
    true_sample = true_df.sample(n=n_sample, random_state=random_state)

    def add_features(sub: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, row in sub.iterrows():
            feats = extract_features(row["prompt"])
            rows.append(
                {
                    "prompt": row["prompt"][:60] + ("..." if len(row["prompt"]) > 60 else ""),
                    "small_sufficient": row["small_sufficient"],
                    **{name: getattr(feats, name) for name in HANDCRAFTED_FEATURE_NAMES},
                }
            )
        return pd.DataFrame(rows)

    false_features = add_features(false_df)
    true_features = add_features(true_sample)

    print("\n" + "=" * 60)
    print("STEP 2 — FEATURE INSPECTION")
    print("=" * 60)
    print("\nHand-crafted features (from features.py):")
    for i, name in enumerate(HANDCRAFTED_FEATURE_NAMES, 1):
        print(f"  {i}. {name}")

    print(f"\n--- small_sufficient=False ({n_false} examples) — hand-crafted vectors ---")
    print(false_features.to_string(index=False))

    print(f"\n--- small_sufficient=True (random sample of {n_sample}) — hand-crafted vectors ---")
    print(true_features.to_string(index=False))

    summary_rows = []
    for name in HANDCRAFTED_FEATURE_NAMES:
        false_vals = false_features[name].astype(float)
        true_vals = true_features[name].astype(float)
        false_mean = false_vals.mean()
        true_mean = true_vals.mean()
        pooled_std = np.std(np.concatenate([false_vals, true_vals]), ddof=0)
        separation = abs(false_mean - true_mean) / pooled_std if pooled_std > 0 else 0.0
        summary_rows.append(
            {
                "feature": name,
                "false_mean": false_mean,
                "true_mean": true_mean,
                "mean_diff": false_mean - true_mean,
                "separation (|diff|/pooled_std)": separation,
            }
        )
    summary = pd.DataFrame(summary_rows)

    print("\n--- Per-feature class means (False vs True sample) ---")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    weak_signal = summary["separation (|diff|/pooled_std)"].max() < 0.5
    return {
        "false_features": false_features,
        "true_features": true_features,
        "summary": summary,
        "weak_signal": weak_signal,
        "max_separation": float(summary["separation (|diff|/pooled_std)"].max()),
    }


def inspect_embedding_separation(df: pd.DataFrame) -> dict:
    from sklearn.metrics.pairwise import cosine_similarity

    prompts = df["prompt"].tolist()
    labels = df["small_sufficient"].astype(bool).values
    embeddings = embed_prompts(prompts)

    false_emb = embeddings[~labels]
    true_emb = embeddings[labels]

    false_centroid = false_emb.mean(axis=0, keepdims=True)
    true_centroid = true_emb.mean(axis=0, keepdims=True)

    false_intra = cosine_similarity(false_emb, false_centroid).mean()
    true_intra = cosine_similarity(true_emb, true_centroid).mean()
    cross_false_to_true = cosine_similarity(false_emb, true_centroid).mean()
    cross_true_to_false = cosine_similarity(true_emb, false_centroid).mean()
    cross_mean = (cross_false_to_true + cross_true_to_false) / 2.0

    print("\n" + "=" * 60)
    print("EMBEDDING SEPARATION (all-MiniLM-L6-v2, 384-dim)")
    print("=" * 60)
    print(f"  False-class intra similarity (to False centroid): {false_intra:.4f}")
    print(f"  True-class intra similarity (to True centroid):  {true_intra:.4f}")
    print(f"  Cross-class False→True centroid:                 {cross_false_to_true:.4f}")
    print(f"  Cross-class True→False centroid:                 {cross_true_to_false:.4f}")
    print(f"  Cross-class average:                             {cross_mean:.4f}")
    print(
        f"  Separation gap (avg intra - cross): "
        f"{((false_intra + true_intra) / 2 - cross_mean):.4f}"
    )

    return {
        "false_intra": float(false_intra),
        "true_intra": float(true_intra),
        "cross_mean": float(cross_mean),
        "separation_gap": float((false_intra + true_intra) / 2 - cross_mean),
    }


def cv_metrics_summary(cv: dict) -> dict[str, float]:
    return {
        "accuracy": cv["accuracy"][0],
        "false_precision": cv["False"]["precision"][0],
        "false_recall": cv["False"]["recall"][0],
        "false_f1": cv["False"]["f1"][0],
        "true_precision": cv["True"]["precision"][0],
        "true_recall": cv["True"]["recall"][0],
        "true_f1": cv["True"]["f1"][0],
    }


def print_before_after_table(baseline: dict, combined: dict) -> None:
    print("\n" + "=" * 60)
    print("BEFORE/AFTER CV COMPARISON (5-fold, threshold=0.50)")
    print("=" * 60)
    print(
        f"{'metric':<22}  {'6 hand-crafted':>16}  {'6 + embedding':>16}  {'delta':>10}"
    )
    rows = [
        ("accuracy", "accuracy"),
        ("False precision", "false_precision"),
        ("False recall", "false_recall"),
        ("False F1", "false_f1"),
        ("True precision", "true_precision"),
        ("True recall", "true_recall"),
        ("True F1", "true_f1"),
    ]
    for label, key in rows:
        old = baseline[key]
        new = combined[key]
        delta = new - old
        print(f"{label:<22}  {old:16.4f}  {new:16.4f}  {delta:+10.4f}")


def meaningful_improvement(baseline: dict, combined: dict, min_f1_gain: float = 0.03) -> bool:
    return combined["false_f1"] >= baseline["false_f1"] + min_f1_gain


def print_cv_metrics(cv: dict) -> None:
    print("\n" + "=" * 60)
    print(f"STRATIFIED {cv['n_splits']}-FOLD CV (threshold={cv['threshold']:.2f})")
    print("=" * 60)
    acc_mean, acc_std = cv["accuracy"]
    print(f"Accuracy:  {acc_mean:.4f} ± {acc_std:.4f}")
    print()
    print(format_confusion_matrix(cv["aggregated_cm"]))
    print()
    print("Per-class metrics (mean ± std across folds):")
    for cls, label in [
        ("False", "small_sufficient=False (high complexity)"),
        ("True", "small_sufficient=True (low complexity)"),
    ]:
        print(f"  {label}:")
        for metric in ("precision", "recall", "f1"):
            mean, std = cv[cls][metric]
            print(f"    {metric}: {mean:.4f} ± {std:.4f}")


def print_threshold_table(rows: list[dict]) -> dict | None:
    print("\n" + "=" * 60)
    print("THRESHOLD SWEEP (out-of-fold, False class metrics)")
    print("=" * 60)
    print(
        f"{'threshold':>10}  {'acc':>6}  "
        f"{'F_prec':>7}  {'F_rec':>7}  {'F_f1':>7}  "
        f"{'T_prec':>7}  {'T_rec':>7}  {'T_f1':>7}"
    )
    best_f1 = None
    best_row = None
    for row in rows:
        print(
            f"{row['threshold']:10.2f}  {row['accuracy']:6.3f}  "
            f"{row['false_precision']:7.3f}  {row['false_recall']:7.3f}  {row['false_f1']:7.3f}  "
            f"{row['true_precision']:7.3f}  {row['true_recall']:7.3f}  {row['true_f1']:7.3f}"
        )
        if best_f1 is None or row["false_f1"] > best_f1:
            best_f1 = row["false_f1"]
            best_row = row
    return best_row


def recommend_precision_threshold(
    rows: list[dict],
    *,
    min_false_recall: float = 0.5,
    target_false_precision: float = 0.45,
) -> tuple[dict | None, dict | None]:
    """
    Pick threshold with False recall >= min_false_recall and precision nearest target.
    Also returns best-precision row (any recall) for reporting when floor is unreachable.
    """
    eligible = [r for r in rows if r["false_recall"] >= min_false_recall]
    recommended = None
    if eligible:
        recommended = min(
            eligible,
            key=lambda r: (
                abs(r["false_precision"] - target_false_precision),
                -r["false_precision"],
            ),
        )
    best_precision = max(rows, key=lambda r: r["false_precision"])
    return recommended, best_precision


def print_precision_recommendation(
    recommended: dict | None,
    best_precision: dict | None,
) -> None:
    print("\n" + "=" * 60)
    print("RECOMMENDED THRESHOLD (precision-focused, recall floor 0.50)")
    print("=" * 60)
    if recommended is None:
        print("No threshold met False recall >= 0.50.")
    else:
        print(
            f"threshold={recommended['threshold']:.2f}  "
            f"False precision={recommended['false_precision']:.3f}  "
            f"False recall={recommended['false_recall']:.3f}  "
            f"False F1={recommended['false_f1']:.3f}  "
            f"accuracy={recommended['accuracy']:.3f}"
        )
    if best_precision is not None:
        print(
            f"\nBest False precision in sweep: threshold={best_precision['threshold']:.2f}  "
            f"False precision={best_precision['false_precision']:.3f}  "
            f"False recall={best_precision['false_recall']:.3f}"
        )
    print("(Recommendation only — not locked into policy.yaml or predict.py yet.)")


def print_baseline_enhanced_table(baseline: dict, enhanced: dict, *, threshold: float) -> None:
    print("\n" + "=" * 60)
    print(f"BEFORE/AFTER CV (5-fold, enhanced @ threshold={threshold:.2f})")
    print("=" * 60)
    print(f"{'metric':<22}  {'6 legacy @0.50':>16}  {'12 feat @tuned':>16}  {'delta':>10}")
    rows = [
        ("accuracy", "accuracy"),
        ("False precision", "false_precision"),
        ("False recall", "false_recall"),
        ("False F1", "false_f1"),
        ("True precision", "true_precision"),
        ("True recall", "true_recall"),
        ("True F1", "true_f1"),
    ]
    for label, key in rows:
        old = baseline[key]
        new = enhanced[key]
        delta = new - old
        print(f"{label:<22}  {old:16.4f}  {new:16.4f}  {delta:+10.4f}")


def train_single_split(
    data_path: Path,
    output_path: Path,
    random_state: int = 42,
    *,
    class_weight: str | dict | None = "balanced",
    use_embeddings: bool = True,
) -> dict:
    df = load_dataset(data_path)
    X = build_feature_matrix(df["prompt"].tolist(), use_embeddings=use_embeddings)
    y = df["small_sufficient"].astype(bool).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    model = make_model(random_state, class_weight)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    by_class = per_class_metrics(y_test, y_pred)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    return {
        "accuracy": by_class["accuracy"],
        "by_class": by_class,
        "confusion_matrix_text": format_confusion_matrix(
            confusion_matrix(y_test, y_pred, labels=CLASS_LABELS)
        ),
        "degenerate": is_degenerate(y_pred),
        "report": classification_report(y_test, y_pred, labels=CLASS_LABELS, zero_division=0),
    }


def print_single_split(metrics: dict) -> None:
    print("\n" + "=" * 60)
    print("SINGLE 80/20 SPLIT (for comparison — less reliable at n=150)")
    print("=" * 60)
    print(f"Overall accuracy: {metrics['accuracy']:.4f}")
    print()
    print(metrics["confusion_matrix_text"])
    print()
    for cls, label in [
        ("False", "small_sufficient=False"),
        ("True", "small_sufficient=True"),
    ]:
        m = metrics["by_class"][cls]
        print(
            f"  {label}: precision={m['precision']:.4f} "
            f"recall={m['recall']:.4f} f1={m['f1']:.4f}"
        )
    if metrics["degenerate"]:
        print("\nWARNING: single-split model is degenerate.")
    print("-" * 60)
    print(metrics["report"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train complexity classifier")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument(
        "--no-balanced",
        action="store_true",
        help="Disable class_weight='balanced'",
    )
    parser.add_argument(
        "--handcrafted-only",
        action="store_true",
        help="Train and evaluate with hand-crafted features only (no embeddings)",
    )
    parser.add_argument(
        "--skip-inspection",
        action="store_true",
        help="Skip verbose per-row feature inspection tables",
    )
    args = parser.parse_args()

    class_weight = None if args.no_balanced else "balanced"
    df = load_dataset(args.data)
    prompts = df["prompt"].tolist()
    y = df["small_sufficient"].astype(bool).values

    print("=" * 60)
    print("CLASS DISTRIBUTION")
    print("=" * 60)
    print_class_distribution(y, "Full dataset")

    print("\n" + "=" * 60)
    print("STEP 2a — HAND-CRAFTED FEATURE INSPECTION")
    print("=" * 60)
    if args.skip_inspection:
        from packages.complexity_classifier.features import extract_features

        handcrafted_report = {"max_separation": 0.0, "weak_signal": False}
        print(f"Skipped (--skip-inspection). {len(HANDCRAFTED_FEATURE_NAMES)} features:")
        for i, name in enumerate(HANDCRAFTED_FEATURE_NAMES, 1):
            print(f"  {i}. {name}")
    else:
        handcrafted_report = inspect_handcrafted_features(df, random_state=args.random_state)
    X_handcrafted = build_feature_matrix(prompts, use_embeddings=False)
    X_legacy = X_handcrafted[:, :LEGACY_HANDCRAFTED_DIM]

    print("\n" + "=" * 60)
    print(f"STEP 1 — CV: {LEGACY_HANDCRAFTED_DIM} LEGACY FEATURES (threshold=0.50)")
    print("=" * 60)
    cv_baseline = cross_validate(
        X_legacy,
        y,
        n_splits=args.folds,
        random_state=args.random_state,
        class_weight=class_weight,
    )
    print_cv_metrics(cv_baseline)
    baseline_summary = cv_metrics_summary(cv_baseline)

    if args.handcrafted_only:
        print("\n" + "=" * 60)
        print("STEP 1b — THRESHOLD SWEEP (6 legacy features, n=300)")
        print("=" * 60)
        threshold_rows = threshold_sweep_cv(
            X_legacy,
            y,
            n_splits=args.folds,
            random_state=args.random_state,
            class_weight=class_weight,
        )
        print_threshold_table(threshold_rows)
        recommended, best_precision = recommend_precision_threshold(threshold_rows)
        print_precision_recommendation(recommended, best_precision)
        chosen_threshold = recommended["threshold"] if recommended else 0.5

        legacy_at_threshold = cross_validate(
            X_legacy,
            y,
            n_splits=args.folds,
            random_state=args.random_state,
            class_weight=class_weight,
            threshold=chosen_threshold,
        )
        legacy_summary = cv_metrics_summary(legacy_at_threshold)

        print("\n" + "=" * 60)
        print(
            f"STEP 3 — CV: {len(HANDCRAFTED_FEATURE_NAMES)} FEATURES "
            f"(6 legacy + 6 pattern), threshold={chosen_threshold:.2f}"
        )
        print("=" * 60)
        cv_enhanced = cross_validate(
            X_handcrafted,
            y,
            n_splits=args.folds,
            random_state=args.random_state,
            class_weight=class_weight,
            threshold=chosen_threshold,
        )
        print_cv_metrics(cv_enhanced)
        enhanced_summary = cv_metrics_summary(cv_enhanced)

        print_baseline_enhanced_table(baseline_summary, enhanced_summary, threshold=chosen_threshold)

        print("\n" + "=" * 60)
        print("REFERENCE — prior 300-row baseline (6 feat, threshold=0.50)")
        print("=" * 60)
        print(
            "accuracy=0.673  False prec=0.287  False rec=0.772  False F1=0.416"
        )

        single = train_single_split(
            args.data,
            args.output,
            random_state=args.random_state,
            class_weight=class_weight,
            use_embeddings=False,
        )
        print_single_split(single)
        print(
            f"\nModel saved to: {args.output.resolve()} "
            f"(12 hand-crafted features, 80/20 split)"
        )

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Hand-crafted max separation: {handcrafted_report['max_separation']:.3f}")
        print(f"Recommended threshold: {chosen_threshold:.2f}")
        print(
            f"False precision @ recommended threshold: "
            f"{legacy_summary['false_precision']:.4f} (legacy 6 feat) → "
            f"{enhanced_summary['false_precision']:.4f} (12 feat)"
        )
        print(
            f"False F1 @ recommended threshold: "
            f"{legacy_summary['false_f1']:.4f} → {enhanced_summary['false_f1']:.4f}"
        )
        if best_precision and best_precision["false_precision"] >= 0.40:
            print("Note: best precision in sweep reached >= 0.40 but may be below recall floor.")
        precision_gain = enhanced_summary["false_precision"] - baseline_summary["false_precision"]
        if enhanced_summary["false_precision"] >= 0.40:
            print("Verdict: False precision reached usable range (>= 0.40).")
        elif precision_gain >= 0.05:
            print("Verdict: Meaningful precision gain, but still below 0.40 target.")
        else:
            print(
                "Verdict: PRECISION PLATEAU — threshold sweep and pattern features did not "
                "meaningfully improve False precision above ~0.29 (best sweep: "
                f"{best_precision['false_precision']:.3f} @ {best_precision['threshold']:.2f}). "
                "Consider accepting high-recall / lower-precision as the final design."
            )
        return

    embedding_report = inspect_embedding_separation(df)
    X_combined = build_feature_matrix(prompts, use_embeddings=True)

    print("\n" + "=" * 60)
    print("STEP 1 — CV: 6 HAND-CRAFTED + 384 EMBEDDING FEATURES")
    print("=" * 60)
    cv_combined = cross_validate(
        X_combined,
        y,
        n_splits=args.folds,
        random_state=args.random_state,
        class_weight=class_weight,
    )
    print_cv_metrics(cv_combined)
    combined_summary = cv_metrics_summary(cv_combined)

    print_before_after_table(baseline_summary, combined_summary)

    improved = meaningful_improvement(baseline_summary, combined_summary)
    best_threshold = None
    if improved:
        print(
            f"\nMinority-class F1 improved by "
            f"{combined_summary['false_f1'] - baseline_summary['false_f1']:.4f} "
            f"(>= 0.03 threshold) — running threshold sweep on combined features."
        )
        threshold_rows = threshold_sweep_cv(
            X_combined,
            y,
            n_splits=args.folds,
            random_state=args.random_state,
            class_weight=class_weight,
        )
        best_threshold = print_threshold_table(threshold_rows)
    else:
        print(
            "\nMinority-class F1 did NOT meaningfully improve with embeddings "
            f"(delta={combined_summary['false_f1'] - baseline_summary['false_f1']:+.4f}). "
            "Skipping threshold sweep."
        )

    single = train_single_split(
        args.data,
        args.output,
        random_state=args.random_state,
        class_weight=class_weight,
        use_embeddings=True,
    )
    print_single_split(single)
    print(
        f"\nModel saved to: {args.output.resolve()} "
        f"(combined features, 80/20 split)"
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(
        f"Hand-crafted max separation: {handcrafted_report['max_separation']:.3f} "
        f"(word_count best at ~0.41 previously)"
    )
    print(
        f"Embedding separation gap (avg intra - cross): "
        f"{embedding_report['separation_gap']:.4f}"
    )
    if improved:
        print(
            f"Embeddings improved minority F1: "
            f"{baseline_summary['false_f1']:.4f} → {combined_summary['false_f1']:.4f}"
        )
        if best_threshold:
            print(
                f"Best False-class F1 at threshold={best_threshold['threshold']:.2f}: "
                f"F_f1={best_threshold['false_f1']:.3f}"
            )
    else:
        print(
            "Embeddings did NOT meaningfully close the gap on minority-class F1. "
            "Labeling methodology or task definition may need reconsideration."
        )


if __name__ == "__main__":
    main()
