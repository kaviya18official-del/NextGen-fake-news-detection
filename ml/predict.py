"""Inference module for NewsVerify classifiers.

Loads versioned scikit-learn models from disk, applies inference with latency
tracking, uncertainty assessment, and feature attribution.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Any, Optional
import joblib

from ml.explain import explain_prediction

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
PIPELINE_PATH = os.path.join(MODELS_DIR, "pipeline.joblib")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")


class NewsClassifierPredictor:
    """Predictor handling model loading, inference, uncertainty, and explanation."""

    def __init__(
        self,
        pipeline_path: str = PIPELINE_PATH,
        metadata_path: str = METADATA_PATH,
    ):
        self.pipeline_path = pipeline_path
        self.metadata_path = metadata_path
        self.pipeline = None
        self.metadata: Dict[str, Any] = {}
        self._load_model()

    def _load_model(self) -> None:
        """Load pipeline and metadata from disk if available."""
        if os.path.exists(self.pipeline_path):
            self.pipeline = joblib.load(self.pipeline_path)

        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    @property
    def is_available(self) -> bool:
        """Return True if a trained model pipeline is loaded and ready."""
        return self.pipeline is not None

    def predict(self, text: str) -> Dict[str, Any]:
        """Classify input text using the trained model pipeline.

        Raises:
            FileNotFoundError: if model pipeline is not trained yet.
            ValueError: if text input is invalid.
        """
        if not self.is_available:
            raise FileNotFoundError(
                "Model is not available. Please train a model first using: "
                "`python -m ml.train --data data/news_sample.csv`"
            )

        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError("Input text cannot be empty.")

        start_time = time.perf_counter()

        # Predict class
        y_pred = self.pipeline.predict([text])[0]
        prediction_label = str(y_pred)

        # Compute score / probability
        score = None
        score_type = "unknown"
        uncertainty = "Certain"

        classifier = getattr(self.pipeline, "named_steps", {}).get("classifier", self.pipeline.steps[-1][1])

        if hasattr(classifier, "predict_proba"):
            probs = self.pipeline.predict_proba([text])[0]
            classes = list(classifier.classes_)
            pred_idx = classes.index(y_pred)
            score = round(float(probs[pred_idx]), 4)
            score_type = "predicted_probability"

            # Uncertainty check: if probability is close to 50%
            if 0.45 <= score <= 0.55:
                uncertainty = "Borderline / High Uncertainty"
            elif score < 0.65:
                uncertainty = "Moderate Confidence"
            else:
                uncertainty = "High Statistical Confidence"

        elif hasattr(classifier, "decision_function"):
            decision = self.pipeline.decision_function([text])[0]
            score = round(float(abs(decision)), 4)
            score_type = "decision_margin"
            if score < 0.3:
                uncertainty = "Borderline / Narrow Margin"
            else:
                uncertainty = "Clear Margin"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Compute explainability feature attributions
        explanation = explain_prediction(self.pipeline, text, top_k=6)

        version_tag = self.metadata.get("version_tag", "unversioned")
        model_type = self.metadata.get("model_type", type(classifier).__name__)

        limitations = (
            "The ML prediction evaluates statistical text patterns (vocabulary, style, structure) "
            "based on the training distribution. It does NOT independently check real-world facts "
            "and MUST NOT be interpreted as proof that the article is objectively true or false."
        )

        return {
            "prediction": prediction_label,
            "score": score,
            "score_type": score_type,
            "uncertainty": uncertainty,
            "model_version": version_tag,
            "model_type": model_type,
            "processing_time_ms": elapsed_ms,
            "explanation": explanation,
            "limitations": limitations,
        }
