# NextGen NewsVerify — AI-Powered News Analysis & Fact-Checking Assistant

**NextGen NewsVerify** is an investigative decision-support assistant designed for journalists, researchers, and citizens. It analyzes news articles via pasted text, public URLs, or screenshots, extracts checkable factual claims, retrieves published independent fact-checks, matches evidence, explains machine learning predictions, and produces structured forensic verification dossiers.

> **Investigative Principle:** NextGen NewsVerify is an investigative assistant, not an automatic truth detector. It answers five distinct questions independently and **never** collapses them into an unsupported single "truth percentage" or arbitrary weighted score.

---

## 1. The Five Core Investigative Questions

| # | Question | Method |
|---|---|---|
| **1** | **What does the ML model predict about this article?** | Scikit-learn TF-IDF pipeline classifying statistical lexical patterns, with linear feature attribution. |
| **2** | **Which specific claims can be investigated?** | Deterministic factual claim extractor prioritizing numbers, dates, reporting verbs, and assertions. |
| **3** | **Have independent organizations previously reviewed them?** | Google Fact Check Tools API query with caching, quotas, and structured status tracking. |
| **4** | **What evidence is available?** | Lexical similarity comparison (Jaccard + sequence alignment) classifying reviews as relevant, related, or rejected. |
| **5** | **What can responsibly be concluded?** | Deterministic evidence assessment: `prior_fact_check_found`, `no_matching_fact_check`, `insufficient_evidence`, `evidence_conflict`, or `lookup_unavailable`. |

---

## 2. Project Directory Structure

```text
nextgen-newsverify/
├── app.py                      # Main Streamlit portal and navigation hub
├── pages/
│   ├── 1_📊_Dashboard.py        # Verification activity metrics and evidence breakdown
│   ├── 2_🔍_Analyze_News.py     # End-to-end 10-step article analysis (Text & URL)
│   ├── 3_🖼️_Screenshot_Analysis.py # Safe upload, OCR extraction & editable correction
│   ├── 4_🎯_Claim_Verification.py # Deep-dive into individual statements & sensitivity
│   ├── 5_⚖️_Evidence_Comparison.py# Multi-source discrepancy & conflict synthesis
│   ├── 6_📜_Analysis_History.py  # SQLite dossier archive, search, and deletion
│   ├── 7_📈_Model_Performance.py # Held-out test metrics, confusion matrix & calibration
│   └── 8_⚙️_Settings.py         # API key configuration, data retention, security audit
├── ml/
│   ├── train.py                # Reproducible training & 3-model comparison CLI
│   ├── predict.py              # Model inference with latency & uncertainty
│   ├── evaluate.py             # Accuracy, per-class F1, confusion & calibration
│   └── explain.py              # Linear coefficient feature attribution
├── services/
│   ├── article_extractor.py    # SSRF-safe URL retrieval and text normalization
│   ├── claim_extractor.py      # Deterministic sentence segmentation & scoring
│   ├── fact_check_service.py   # Google Fact Check Tools API client with caching
│   ├── claim_matcher.py        # Lexical similarity candidate classification
│   ├── evidence_assessor.py    # Strict deterministic evidence assessment logic
│   ├── source_analyzer.py      # Publisher, byline, timestamp, and context audit
│   ├── ocr_service.py          # Safe image decoding and Tesseract OCR engine
│   └── report_generator.py     # PDF dossiers (ReportLab) and structured JSON exports
├── database/
│   ├── models.py               # SQLAlchemy schema (analyses, claims, reviews, etc.)
│   ├── connection.py           # SQLite connection pool with PRAGMA foreign keys
│   └── repository.py           # Transaction-safe repository with cascading deletion
├── security/
│   ├── url_validator.py        # SSRF defense, private IP & cloud metadata blocking
│   └── input_validator.py      # HTML script stripping, upload validation, secret masking
├── data/
│   ├── news_sample.csv         # Curated realistic dataset (Real & Fake balanced)
│   └── README.md               # Dataset requirements and benchmarks
├── models/
│   ├── pipeline.joblib         # Serialized active Scikit-learn pipeline
│   ├── model_metadata.json     # Empirical metrics and hyperparameters
│   └── README.md               # Model artifacts documentation
├── tests/                      # Comprehensive 38-test pytest suite
├── .env.example                # Environment variables template
├── .gitignore                  # Git exclusion rules
├── requirements.txt            # Locked dependencies
└── README.md                   # Complete architectural and operational manual
```

---

## 3. Installation & Setup Instructions

### Prerequisites
- Python 3.11 or later
- (Optional) [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) for automated image screenshot extraction

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to supply your Google Fact Check API key (optional for local ML analysis; required for live external fact-checking):
```env
GOOGLE_FACTCHECK_API_KEY=AIzaSy...your_key_here
```

---

## 4. Model Training & Evaluation

The training CLI loads the dataset, validates columns, maps labels canonically, deduplicates records, applies stratified 70/15/15 splitting, fits TF-IDF strictly within the training pipeline, trains and validates three candidate architectures (**Logistic Regression**, **Linear SVM**, and **Multinomial Naive Bayes**), selects the optimal model, and evaluates on held-out test data.

### Reproducible Training Command:
```bash
python -m ml.train --data data/news_sample.csv --text-column text --label-column label --model auto
```

### Output:
- Saves pipeline to `models/pipeline.joblib`.
- Saves empirical test metrics and confusion matrix to `models/model_metadata.json`.
- Records active version in SQLite `model_versions` table.

---

## 5. Running the Application

Launch the Streamlit web interface:
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 6. Security Hardening & Defense-in-Depth

1. **SSRF Defense (`security/url_validator.py`)**:
   - Rejects loopback (`127.0.0.0/8`, `::1`), private RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and carrier-grade NAT (`100.64.0.0/10`).
   - Blocks AWS, GCP, and Azure cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
   - Port whitelist strictly enforces `80`, `443`, and `8080`.
   - Re-validates every HTTP redirect hop before following.
2. **HTML Sanitization (`security/input_validator.py`)**:
   - Strips `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`, and inline JavaScript event handlers (`onclick`, `onload`, `onerror`).
3. **Upload Safety**:
   - Caps images at 10 MB and validates headers via PIL `Image.verify()`.
4. **Credential Protection**:
   - API keys are masked (`AIza...cdef`) in all UI displays and logs.

---

## 7. Automated Test Suite

Run the full pytest suite:
```bash
python -m pytest -v
```

All 38 automated unit and integration tests execute with mocked external dependencies to ensure fast, deterministic CI execution without consuming API quota:
- SSRF & private IP blocking
- Input sanitization & HTML stripping
- Image upload validation & path traversal prevention
- SQLite database transactions & cascading deletions
- Deterministic claim extraction & query normalization
- Fact Check API schema parsing, caching, and error handling
- Lexical similarity claim matching & relevance classification
- Evidence assessment states & conflict detection
- ML pipeline training, serialization, reloading, and explainability
- ReportLab PDF generation & JSON export
- Full 10-step end-to-end integration test

---

## 8. Limitations & Methodology

- **Linguistic Patterns vs. Facts:** Text classifiers detect stylistic and vocabulary distributions from their training data. They cannot detect subtle, newly invented falsehoods written in standard journalistic prose.
- **Fact-Check Index Coverage:** The absence of a matching fact-check (`no_matching_fact_check`) does **not** indicate that a statement is true; it merely indicates that no participating organization in the Google Fact Check Tools database has indexed a review for those search terms.
- **Original Ratings Preserved:** Publisher ratings (e.g. "Pants on Fire", "Mostly True", "Misleading") are displayed in their original form rather than converted into a crude binary score.
