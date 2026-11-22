"""Machine Learning package for NextGen NewsVerify.

Includes training, evaluation, explainability, and inference pipelines.
"""

from ml.predict import NewsClassifierPredictor
from ml.explain import explain_prediction

__all__ = [
    "NewsClassifierPredictor",
    "explain_prediction",
]
