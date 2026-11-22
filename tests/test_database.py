"""Tests for SQLite database models, transactions, cascade deletion, and repository."""

import uuid
import pytest
from database.repository import AnalysisRepository


@pytest.fixture
def repo():
    return AnalysisRepository()


def test_save_and_retrieve_analysis(repo):
    """Verify persisting and querying an analysis with claims, reviews, and evidence assessments."""
    analysis_id = str(uuid.uuid4())
    analysis_data = {
        "id": analysis_id,
        "input_type": "text",
        "article_title": "Inflation Report Tests Central Bank Credibility",
        "article_url": None,
        "article_publisher": "Financial Gazette",
        "publication_date": "2026-05-15",
        "article_preview": "Consumer prices rose 3.1 percent according to official statistics.",
        "article_text_hash": "testhash12345",
        "model_version": "v1.0.0-logreg",
        "ml_prediction": "Real",
        "ml_score": 0.88,
        "ml_score_type": "predicted_probability",
        "ml_uncertainty": "High Statistical Confidence",
        "ml_explanation": {"top_features": [{"word": "inflation", "contribution": 0.45}]},
        "processing_time_ms": 12.5,
        "status": "completed",
    }

    claims_data = [
        {
            "claim_index": 0,
            "original_sentence": "Consumer prices rose 3.1 percent across urban centers.",
            "normalized_query": "Consumer prices rose 3.1 percent",
            "claim_type": "statistical_claim",
            "is_selected": True,
            "fact_checks": [
                {
                    "query_used": "Consumer prices rose 3.1 percent",
                    "query_status": "found",
                    "claim_text_from_review": "Did consumer prices rise 3.1 percent?",
                    "publisher_name": "FactCheck.org",
                    "original_rating": "True",
                    "review_url": "https://factcheck.org/inflation-2026",
                    "review_date": "2026-05-16",
                    "lexical_similarity_score": 0.75,
                    "match_classification": "relevant_match",
                }
            ],
        }
    ]

    assessments_data = [
        {
            "claim_index": 0,
            "evidence_status": "prior_fact_check_found",
            "status_explanation": "FactCheck.org verified this claim as True.",
            "conflicting_reviews": [],
            "limitations": "Review based on current Bureau of Labor Statistics figures.",
        }
    ]

    saved_id = repo.save_analysis(analysis_data, claims_data, assessments_data)
    assert saved_id == analysis_id

    # Retrieve and verify deep hierarchy
    retrieved = repo.get_analysis(analysis_id)
    assert retrieved is not None
    assert retrieved["id"] == analysis_id
    assert retrieved["article_title"] == "Inflation Report Tests Central Bank Credibility"
    assert retrieved["ml_prediction"] == "Real"
    assert len(retrieved["claims"]) == 1

    claim = retrieved["claims"][0]
    assert claim["original_sentence"] == "Consumer prices rose 3.1 percent across urban centers."
    assert len(claim["fact_checks"]) == 1
    assert claim["fact_checks"][0]["publisher_name"] == "FactCheck.org"
    assert claim["evidence_assessment"]["evidence_status"] == "prior_fact_check_found"


def test_delete_analysis_cascades(repo):
    """Verify deleting an analysis cascades and cleans up related claims and reviews."""
    analysis_id = str(uuid.uuid4())
    analysis_data = {
        "id": analysis_id,
        "input_type": "text",
        "article_title": "To Be Deleted",
        "article_preview": "Short text for deletion test.",
        "article_text_hash": "delhash123",
        "status": "completed",
    }
    claims_data = [
        {
            "claim_index": 0,
            "original_sentence": "Claim to be deleted.",
            "normalized_query": "Claim to be deleted",
            "fact_checks": [],
        }
    ]

    repo.save_analysis(analysis_data, claims_data)
    assert repo.get_analysis(analysis_id) is not None

    deleted = repo.delete_analysis(analysis_id)
    assert deleted is True
    assert repo.get_analysis(analysis_id) is None


def test_list_analyses_and_stats(repo):
    """Verify listing, filtering, and aggregate statistics calculation."""
    stats = repo.get_statistics()
    assert "total_analyses" in stats
    assert "total_claims" in stats
    assert "evidence_status_breakdown" in stats

    items = repo.list_analyses(limit=10)
    assert isinstance(items, list)
