# Models Directory for NextGen NewsVerify

This directory stores trained model pipelines and associated evaluation metadata.

## Artifacts

- `pipeline.joblib`: Serialized scikit-learn pipeline containing:
  - Text feature extraction (`TfidfVectorizer` with n-grams 1-2, sublinear TF, English stop-word filtering).
  - Selected classifier (e.g. `LogisticRegression`, `LinearSVC`, or `MultinomialNB`).
- `model_metadata.json`: Machine-readable metadata describing:
  - Model architecture and version tag.
  - Training dataset provenance and clean sample counts.
  - Class labels (`Real`, `Fake`).
  - Validation metrics comparing Logistic Regression, Linear SVM, and Multinomial Naive Bayes.
  - Held-out test set metrics (accuracy, macro/weighted precision, recall, F1, per-class metrics, confusion matrix, calibration data).

## Training Command

To re-train or update the active model:
```bash
python -m ml.train --data data/news_sample.csv --text-column text --label-column label
```
