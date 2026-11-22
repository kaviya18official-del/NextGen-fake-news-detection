"""Explainability module for NewsVerify classifiers.

Inspects model coefficients and computes per-token feature contributions
for linear pipelines (Logistic Regression and Linear SVM).
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import numpy as np


def explain_prediction(
    pipeline: Any,
    text: str,
    top_k: int = 8,
) -> Dict[str, Any]:
    """Explain a model prediction on a single document using linear feature attribution.

    Returns:
        Dictionary with influential words, contributions, directional class impact,
        and explicit methodology disclaimer.
    """
    warning_text = (
        "Methodology Disclaimer: Feature contributions reflect statistical vocabulary "
        "correlations learned by the classifier from the training dataset. They highlight "
        "which words shifted the model's classification score, but do NOT prove factual "
        "accuracy, truth, or falsehood."
    )

    try:
        vectorizer = pipeline.named_steps.get("tfidf") or pipeline.steps[0][1]
        classifier = pipeline.named_steps.get("classifier") or pipeline.steps[-1][1]
    except Exception as e:
        return {
            "available": False,
            "reason": f"Pipeline structure does not support coefficient inspection: {e}",
            "warning": warning_text,
        }

    # Verify if classifier has linear coefficients
    if not hasattr(classifier, "coef_"):
        return {
            "available": False,
            "reason": f"Classifier type '{type(classifier).__name__}' does not provide linear coefficients.",
            "warning": warning_text,
        }

    feature_names = np.array(vectorizer.get_feature_names_out())
    classes = getattr(classifier, "classes_", ["Class_0", "Class_1"])
    classes_list = [str(c) for c in classes]

    # Transform document into TF-IDF vector
    x_vec = vectorizer.transform([text])
    if x_vec.nnz == 0:
        return {
            "available": True,
            "top_features": [],
            "class_0_evidence": [],
            "class_1_evidence": [],
            "summary": "None of the vocabulary features in this article matched the model's vocabulary.",
            "warning": warning_text,
        }

    # Extract non-zero indices and their values
    indices = x_vec.indices
    values = x_vec.data

    # For binary classification with shape (1, n_features)
    coefs = classifier.coef_
    if coefs.shape[0] == 1:
        # Binary: class 0 is classes_list[0], class 1 is classes_list[1]
        feature_weights = coefs[0, indices]
        contributions = values * feature_weights

        # Combine into list
        feature_contributions = []
        for feat_idx, val, weight, contrib in zip(indices, values, feature_weights, contributions):
            feature_contributions.append({
                "word": feature_names[feat_idx],
                "tfidf_value": round(float(val), 4),
                "model_weight": round(float(weight), 4),
                "contribution": round(float(contrib), 4),
                "pushed_towards": classes_list[1] if contrib > 0 else classes_list[0],
            })

        # Sort by absolute contribution magnitude
        sorted_by_impact = sorted(feature_contributions, key=lambda f: abs(f["contribution"]), reverse=True)
        top_impact = sorted_by_impact[:top_k]

        # Break down by class
        push_cls_1 = [f for f in sorted_by_impact if f["contribution"] > 0][:top_k]
        push_cls_0 = [f for f in sorted_by_impact if f["contribution"] < 0][:top_k]

        return {
            "available": True,
            "classes": classes_list,
            "top_features": top_impact,
            f"pushes_toward_{classes_list[1]}": push_cls_1,
            f"pushes_toward_{classes_list[0]}": push_cls_0,
            "warning": warning_text,
        }

    return {
        "available": False,
        "reason": "Multiclass coefficient attribution not configured for binary interface.",
        "warning": warning_text,
    }


def get_global_top_features(pipeline: Any, top_n: int = 15) -> Dict[str, Any]:
    """Retrieve the overall highest-weighted vocabulary features learned during training."""
    try:
        vectorizer = pipeline.named_steps.get("tfidf") or pipeline.steps[0][1]
        classifier = pipeline.named_steps.get("classifier") or pipeline.steps[-1][1]
        feature_names = np.array(vectorizer.get_feature_names_out())
        classes = getattr(classifier, "classes_", ["Class_0", "Class_1"])
        classes_list = [str(c) for c in classes]

        if hasattr(classifier, "coef_") and classifier.coef_.shape[0] == 1:
            coefs = classifier.coef_[0]
            top_cls_1_indices = np.argsort(coefs)[-top_n:][::-1]
            top_cls_0_indices = np.argsort(coefs)[:top_n]

            return {
                f"top_indicators_for_{classes_list[1]}": [
                    {"word": feature_names[idx], "weight": round(float(coefs[idx]), 4)}
                    for idx in top_cls_1_indices
                ],
                f"top_indicators_for_{classes_list[0]}": [
                    {"word": feature_names[idx], "weight": round(float(coefs[idx]), 4)}
                    for idx in top_cls_0_indices
                ],
            }
    except Exception as e:
        return {"error": str(e)}

    return {}
