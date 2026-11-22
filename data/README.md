# Dataset Guidelines for NextGen NewsVerify

This directory holds datasets for training and evaluating text classification models.

## Pre-loaded Dataset

- `news_sample.csv`: A curated collection of verified factual news articles and debunked false/conspiracy articles, balanced across political, health, science, and economic topics.

### Dataset Schema Requirements

Any CSV dataset used for training must provide:
- A text column containing the article headline or body text (default: `text`).
- A label column indicating the class (default: `label`).

Acceptable label formats include:
- Binary: `0` / `1`
- Text: `Real` / `Fake`, `reliable` / `unreliable`, `true` / `false`

The training pipeline automatically normalizes these labels to canonical `Real` and `Fake` classes, deduplicates articles to prevent data leakage, and performs stratified splitting across training (70%), validation (15%), and held-out test (15%) partitions.

## Training Command Example

```bash
python -m ml.train --data data/news_sample.csv --text-column text --label-column label
```

## Recommended External Benchmark Datasets
- **WELFake Dataset**: 72,000+ public news articles combining Kaggle, McIntire, Reuters, and BuzzFeed datasets.
- **ISOT Fake News Dataset**: 44,000+ articles from Reuters and flagged sources.
- **LIAR Benchmark**: 12,800 human-labeled short statements from PolitiFact.
