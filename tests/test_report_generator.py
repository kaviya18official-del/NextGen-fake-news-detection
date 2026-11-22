"""Tests for ReportLab PDF generation and JSON export in services/report_generator.py."""

import json
from services.report_generator import ReportGenerator


def test_generate_json_report():
    """Verify JSON serialization contains all required forensic fields."""
    sample_analysis = {
        "id": "test-uuid-1234",
        "article_title": "Sample Verification Dossier",
        "ml_prediction": "Real",
        "ml_score": 0.82,
        "claims": [],
        "status": "completed",
    }
    json_out = ReportGenerator.generate_json_report(sample_analysis)
    parsed = json.loads(json_out)
    assert parsed["id"] == "test-uuid-1234"
    assert parsed["article_title"] == "Sample Verification Dossier"
    assert parsed["ml_prediction"] == "Real"


def test_generate_pdf_report_valid_bytes():
    """Verify ReportLab compiles a valid PDF byte document."""
    sample_analysis = {
        "id": "dossier-uuid-5678",
        "article_title": "Global Climate Conference Outcomes",
        "article_url": "https://example.com/climate",
        "article_publisher": "Science Dispatch",
        "publication_date": "2026-06-01",
        "ml_prediction": "Real",
        "ml_score": 0.89,
        "ml_score_type": "predicted_probability",
        "ml_uncertainty": "High Statistical Confidence",
        "model_version": "v1.0.0-logreg",
        "claims": [
            {
                "claim_index": 0,
                "original_sentence": "Renewable energy production doubled over the last five years.",
                "evidence_assessment": {
                    "evidence_status": "prior_fact_check_found",
                    "status_explanation": "Verified by Energy Facts Alliance.",
                },
                "fact_checks": [
                    {
                        "publisher_name": "Energy Facts Alliance",
                        "original_rating": "Correct",
                        "review_url": "https://energyfacts.org/review/123",
                        "match_classification": "relevant_match",
                    }
                ],
            }
        ],
    }

    pdf_bytes = ReportGenerator.generate_pdf_report(sample_analysis)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Standard PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")
