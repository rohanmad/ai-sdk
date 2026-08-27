"""Load trained complexity classifier and predict complexity score."""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path

from packages.complexity_classifier.vectorize import prompt_to_array

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"


@lru_cache(maxsize=1)
def _load_model(model_path: str):
    with open(model_path, "rb") as f:
        return pickle.load(f)


def predict_complexity(
    prompt: str,
    model_path: str | Path | None = None,
) -> tuple[float, bool, float]:
    """
    Predict complexity from prompt text.

    Returns:
        complexity_score: float in [0, 1] where higher = more complex
        small_sufficient: predicted label (True = low complexity)
        confidence: probability of predicted class
    """
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Complexity classifier not found at {path}. "
            "Run packages/complexity_classifier/train.py first."
        )

    model = _load_model(str(path.resolve()))
    features = prompt_to_array(prompt).reshape(1, -1)

    proba = model.predict_proba(features)[0]
    # Class 0 = small_sufficient False (high complexity), class 1 = True (low)
    classes = list(model.classes_)
    if False in classes and True in classes:
        idx_false = classes.index(False)
        idx_true = classes.index(True)
    else:
        idx_false, idx_true = 0, 1

    p_small_sufficient = float(proba[idx_true])
    small_sufficient = p_small_sufficient >= 0.5
    complexity_score = 1.0 - p_small_sufficient
    confidence = float(max(proba))

    return complexity_score, small_sufficient, confidence
