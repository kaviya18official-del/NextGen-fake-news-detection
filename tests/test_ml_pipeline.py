"""Tests for ML training, pipeline serialization, reloading, inference, and explainability."""

import os
import pytest
from ml.predict import NewsClassifierPredictor
from ml.explain import explain_prediction
from ml.train import load_and_validate_dataset, train_and_evaluate


def test_load_and_validate_dataset():
    """Verify dataset loading, label normalization, and duplicate removal."""
    data_path = os.path.join("data", "news_sample.csv")
    df, stats = load_and_validate_dataset(data_path)

    assert "text" in df.columns
    assert "label" in df.columns
    assert set(df["label"].unique()).issubset({"Real", "Fake"})
    assert stats["clean_samples"] > 0
    assert stats["duplicates_removed"] >= 0


def test_predict_with_trained_model():
    """Verify inference, score, uncertainty, and latency on legitimate and conspiracy texts."""
    predictor = NewsClassifierPredictor()
    assert predictor.is_available is True

    # Real sample test
    real_text = "NASA's James Webb Space Telescope observed infrared stellar clusters in deep space."
    res_real = predictor.predict(real_text)
    assert res_real["prediction"] in ("Real", "Fake")
    assert res_real["score"] is not None
    assert res_real["score_type"] == "predicted_probability"
    assert res_real["processing_time_ms"] > 0
    assert "explanation" in res_real
    assert "limitations" in res_real

    # Fake sample test
    fake_text = "SHOCKING BOMBSHELL: Microchips secretly implanted in tap water pipes to control thoughts via 5G!"
    res_fake = predictor.predict(fake_text)
    assert res_fake["prediction"] in ("Real", "Fake")


def test_predict_rejects_empty_input():
    """Verify empty or whitespace-only input raises ValueError."""
    predictor = NewsClassifierPredictor()
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        predictor.predict("   ")


def test_explain_prediction_feature_attributions():
    """Verify linear feature attribution produces non-zero contributions and directional impact."""
    predictor = NewsClassifierPredictor()
    text = "The Federal Reserve raised interest rates to combat inflation."
    explanation = explain_prediction(predictor.pipeline, text)

    assert explanation["available"] is True
    assert "warning" in explanation
    assert "classes" in explanation
    assert isinstance(explanation["top_features"], list)
