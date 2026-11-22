"""Tests for deterministic evidence status logic in services/evidence_assessor.py."""

from services.evidence_assessor import EvidenceAssessor


def test_evidence_status_prior_fact_check_found():
    """Verify prior_fact_check_found when a relevant review exists."""
    assessor = EvidenceAssessor()
    matched_reviews = [
        {
            "publisher_name": "PolitiFact",
            "original_rating": "False",
            "match_classification": "relevant_match",
            "review_url": "https://politifact.com/example",
            "review_date": "2024-02-01",
        }
    ]

    res = assessor.assess_claim_evidence(query_status="found", matched_reviews=matched_reviews)
    assert res["evidence_status"] == "prior_fact_check_found"
    assert "PolitiFact" in res["status_explanation"]


def test_evidence_status_no_matching_fact_check():
    """Verify no_matching_fact_check when query succeeded but returned 0 results."""
    assessor = EvidenceAssessor()
    res = assessor.assess_claim_evidence(query_status="no_match", matched_reviews=[])
    assert res["evidence_status"] == "no_matching_fact_check"
    assert "No matching fact-check was found in the sources searched" in res["status_explanation"]
    assert "does not establish whether the claim is true or false" in res["status_explanation"]


def test_evidence_status_evidence_conflict():
    """Verify evidence_conflict when multiple publishers have contradictory ratings."""
    assessor = EvidenceAssessor()
    matched_reviews = [
        {
            "publisher_name": "Publisher A",
            "original_rating": "False",
            "match_classification": "relevant_match",
            "review_url": "https://pub-a.com/fact",
            "review_date": "2024-01-01",
        },
        {
            "publisher_name": "Publisher B",
            "original_rating": "True / Verified",
            "match_classification": "relevant_match",
            "review_url": "https://pub-b.com/fact",
            "review_date": "2024-01-05",
        },
    ]

    res = assessor.assess_claim_evidence(query_status="found", matched_reviews=matched_reviews)
    assert res["evidence_status"] == "evidence_conflict"
    assert len(res["conflicting_reviews"]) == 2


def test_evidence_status_lookup_unavailable():
    """Verify lookup_unavailable when API key is missing or network fails."""
    assessor = EvidenceAssessor()
    res = assessor.assess_claim_evidence(query_status="unavailable", matched_reviews=[])
    assert res["evidence_status"] == "lookup_unavailable"
    assert "could not be completed" in res["status_explanation"]
