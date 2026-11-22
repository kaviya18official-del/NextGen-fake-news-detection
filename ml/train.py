"""Training and model selection pipeline for NewsVerify classifiers.

Usage:
    python -m ml.train --data data/news_sample.csv --text-column text --label-column label

Performs validation, deduplication, stratified splitting, comparison of
Logistic Regression, Linear SVM, and Multinomial Naive Bayes, and serializes
the best pipeline along with comprehensive test evaluation metrics.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from typing import Dict, Any, Tuple
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from ml.evaluate import compute_evaluation_metrics
from database.repository import AnalysisRepository

# Standard label mapping dictionary
DEFAULT_LABEL_MAPPING = {
    "0": "Real",
    "1": "Fake",
    0: "Real",
    1: "Fake",
    "real": "Real",
    "fake": "Fake",
    "true": "Real",
    "false": "Fake",
    "reliable": "Real",
    "unreliable": "Fake",
}


def load_and_validate_dataset(
    data_path: str,
    text_column: str = "text",
    label_column: str = "label",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load, validate, normalize labels, and deduplicate dataset."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset file not found at: {data_path}")

    df = pd.read_csv(data_path)

    if text_column not in df.columns:
        raise ValueError(
            f"Missing required text column '{text_column}'. Available columns: {list(df.columns)}"
        )
    if label_column not in df.columns:
        raise ValueError(
            f"Missing required label column '{label_column}'. Available columns: {list(df.columns)}"
        )

    initial_count = len(df)

    # Drop nulls and empty strings
    df = df.dropna(subset=[text_column, label_column]).copy()
    df[text_column] = df[text_column].astype(str).str.strip()
    df = df[df[text_column].str.len() > 10].copy()

    # Map labels to canonical labels
    def map_label(val: Any) -> str:
        s = str(val).strip().lower()
        if s in DEFAULT_LABEL_MAPPING:
            return DEFAULT_LABEL_MAPPING[s]
        # Return capitalized representation if not in standard dictionary
        return str(val).strip().capitalize()

    df[label_column] = df[label_column].apply(map_label)

    # Check for duplicate texts to prevent train/test leakage
    duplicates_count = int(df.duplicated(subset=[text_column]).sum())
    df = df.drop_duplicates(subset=[text_column]).copy()

    clean_count = len(df)
    class_distribution = df[label_column].value_counts().to_dict()

    if len(class_distribution) < 2:
        raise ValueError(f"Dataset must contain at least 2 distinct classes. Found: {class_distribution}")

    stats = {
        "initial_samples": initial_count,
        "clean_samples": clean_count,
        "duplicates_removed": duplicates_count,
        "class_distribution": class_distribution,
    }

    return df, stats


def train_and_evaluate(
    data_path: str,
    text_column: str = "text",
    label_column: str = "label",
    model_choice: str = "auto",
    output_dir: str = "models",
    version_tag: str | None = None,
) -> Dict[str, Any]:
    """Execute complete training, comparison, and evaluation workflow."""
    print(f"[*] Loading dataset from: {data_path}")
    df, stats = load_and_validate_dataset(data_path, text_column, label_column)
    print(f"    - Cleaned samples: {stats['clean_samples']} (Duplicates removed: {stats['duplicates_removed']})")
    print(f"    - Class distribution: {stats['class_distribution']}")

    X = df[text_column].tolist()
    y = df[label_column].tolist()
    classes = sorted(list(set(y)))

    # Split: Train (70%), Validation (15%), Test (15%) with stratification
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    val_ratio = 0.15 / (1.0 - 0.15)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_ratio, random_state=42, stratify=y_train_val
    )

    print(f"[*] Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    # Candidate models for comparison
    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42, C=1.0),
        "LinearSVC": LinearSVC(random_state=42, dual=False, max_iter=2000),
        "MultinomialNB": MultinomialNB(alpha=0.5),
    }

    val_results = {}
    fitted_pipelines = {}

    print("[*] Training and comparing candidate models on validation split...")
    for name, clf in candidates.items():
        # TF-IDF fitted strictly inside the pipeline on train split only
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=10000,
                sublinear_tf=True,
                stop_words="english",
            )),
            ("classifier", clf),
        ])

        pipeline.fit(X_train, y_train)
        fitted_pipelines[name] = pipeline

        # Validate
        y_val_pred = pipeline.predict(X_val)
        y_val_prob = None
        if hasattr(clf, "predict_proba"):
            probs = pipeline.predict_proba(X_val)
            if len(classes) == 2:
                y_val_prob = probs[:, 1]

        val_metrics = compute_evaluation_metrics(y_val, y_val_pred, y_val_prob, classes=classes)
        val_results[name] = val_metrics
        print(f"    -> {name}: Validation Acc={val_metrics['accuracy']:.4f}, Macro-F1={val_metrics['macro_f1']:.4f}")

    # Select best model
    if model_choice != "auto" and model_choice in candidates:
        selected_name = model_choice
    else:
        # Default selection: highest Macro-F1 on validation set
        selected_name = max(val_results, key=lambda k: val_results[k]["macro_f1"])

    print(f"[+] Selected model: {selected_name}")
    selected_pipeline = fitted_pipelines[selected_name]

    # Evaluate selected model on held-out TEST set
    y_test_pred = selected_pipeline.predict(X_test)
    y_test_prob = None
    if hasattr(selected_pipeline.named_steps["classifier"], "predict_proba"):
        probs = selected_pipeline.predict_proba(X_test)
        if len(classes) == 2:
            y_test_prob = probs[:, 1]

    test_metrics = compute_evaluation_metrics(y_test, y_test_pred, y_test_prob, classes=classes)
    print(f"[+] Held-out Test Set Performance:")
    print(f"    - Accuracy:  {test_metrics['accuracy']:.4f}")
    print(f"    - Macro F1:  {test_metrics['macro_f1']:.4f}")
    print(f"    - Confusion: {test_metrics['confusion_matrix']['matrix']}")

    # Prepare version tag and metadata
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    if not version_tag:
        version_tag = f"v1.0.0-{selected_name.lower()}-{now_str}"

    os.makedirs(output_dir, exist_ok=True)
    pipeline_out = os.path.join(output_dir, "pipeline.joblib")
    metadata_out = os.path.join(output_dir, "model_metadata.json")

    joblib.dump(selected_pipeline, pipeline_out)

    metadata = {
        "version_tag": version_tag,
        "model_type": selected_name,
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dataset_source": os.path.basename(data_path),
        "dataset_stats": stats,
        "classes": classes,
        "split_sizes": {
            "train": len(X_train),
            "val": len(X_val),
            "test": len(X_test),
        },
        "validation_comparison": {
            k: {
                "accuracy": v["accuracy"],
                "macro_f1": v["macro_f1"],
                "macro_precision": v["macro_precision"],
                "macro_recall": v["macro_recall"],
            }
            for k, v in val_results.items()
        },
        "test_metrics": test_metrics,
    }

    with open(metadata_out, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Record model version in database
    try:
        repo = AnalysisRepository()
        repo.save_model_version({
            "version_tag": version_tag,
            "model_type": selected_name,
            "dataset_source": os.path.basename(data_path),
            "num_samples": stats["clean_samples"],
            "accuracy": test_metrics["accuracy"],
            "precision": test_metrics["macro_precision"],
            "recall": test_metrics["macro_recall"],
            "f1_score": test_metrics["macro_f1"],
            "is_active": True,
            "metadata": metadata,
        })
        print(f"[+] Model version recorded in database.")
    except Exception as e:
        print(f"[!] Warning: Could not record model in database: {e}")

    print(f"[+] Saved pipeline to: {pipeline_out}")
    print(f"[+] Saved metadata to: {metadata_out}")

    return metadata


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate NewsVerify classifiers.")
    parser.add_argument("--data", required=True, help="Path to input news CSV file.")
    parser.add_argument("--text-column", default="text", help="Name of text column.")
    parser.add_argument("--label-column", default="label", help="Name of label column.")
    parser.add_argument(
        "--model",
        default="auto",
        choices=["auto", "LogisticRegression", "LinearSVC", "MultinomialNB"],
        help="Model choice or auto comparison.",
    )
    parser.add_argument("--output-dir", default="models", help="Directory to save pipeline and metadata.")
    parser.add_argument("--version-tag", default=None, help="Optional version tag.")

    args = parser.parse_args()

    try:
        train_and_evaluate(
            data_path=args.data,
            text_column=args.text_column,
            label_column=args.label_column,
            model_choice=args.model,
            output_dir=args.output_dir,
            version_tag=args.version_tag,
        )
    except Exception as e:
        print(f"Error during training: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
