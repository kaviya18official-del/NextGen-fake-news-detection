"""Evaluation metrics and calibration assessment for NewsVerify classifiers.

Calculates accuracy, per-class metrics, confusion matrices, and calibration data
on held-out splits without data leakage.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    brier_score_loss,
)
from sklearn.calibration import calibration_curve


def compute_evaluation_metrics(
    y_true: List[str] | np.ndarray,
    y_pred: List[str] | np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate comprehensive classification metrics and confusion matrix."""
    if classes is None:
        classes = sorted(list(set(y_true) | set(y_pred)))

    acc = float(accuracy_score(y_true, y_pred))

    # Macro & Weighted metrics
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, average="macro", zero_division=0
    )
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, average="weighted", zero_division=0
    )

    # Per-class breakdown
    p_class, r_class, f1_class, support = precision_recall_fscore_support(
        y_true, y_pred, labels=classes, average=None, zero_division=0
    )

    per_class_metrics = {}
    for i, cls_name in enumerate(classes):
        per_class_metrics[cls_name] = {
            "precision": round(float(p_class[i]), 4),
            "recall": round(float(r_class[i]), 4),
            "f1_score": round(float(f1_class[i]), 4),
            "support": int(support[i]),
        }

    cm = confusion_matrix(y_true, y_pred, labels=classes)

    metrics: Dict[str, Any] = {
        "accuracy": round(acc, 4),
        "macro_precision": round(float(p_macro), 4),
        "macro_recall": round(float(r_macro), 4),
        "macro_f1": round(float(f1_macro), 4),
        "weighted_f1": round(float(f1_wt), 4),
        "per_class": per_class_metrics,
        "confusion_matrix": {
            "matrix": cm.tolist(),
            "labels": classes,
        },
        "sample_count": len(y_true),
    }

    # Binary calibration evaluation if probabilities provided and binary
    if y_prob is not None and len(classes) == 2:
        try:
            # Assume classes[1] is the positive class
            pos_label = classes[1]
            y_binary = np.array([1 if y == pos_label else 0 for y in y_true])
            brier = float(brier_score_loss(y_binary, y_prob))
            prob_true, prob_pred = calibration_curve(y_binary, y_prob, n_bins=5, strategy="uniform")
            metrics["calibration"] = {
                "brier_score": round(brier, 4),
                "positive_label": pos_label,
                "fraction_of_positives": [round(float(v), 4) for v in prob_true],
                "mean_predicted_value": [round(float(v), 4) for v in prob_pred],
            }
        except Exception as e:
            metrics["calibration_error"] = str(e)

    return metrics
