"""Tests for lexical similarity claim matching and candidate filtering in services/claim_matcher.py."""

from services.claim_matcher import ClaimMatcher


def test_claim_matcher_high_relevance():
    """Verify that closely phrased claims achieve high similarity score and relevant_match tag."""
    matcher = ClaimMatcher(relevance_threshold=0.30)
    claim_sentence = "NASA James Webb Space Telescope discovers ancient distant galaxy cluster."

    candidate_reviews = [
        {
            "claim_text_from_review": "James Webb Space Telescope detects ancient galaxy cluster in deep space",
            "publisher_name": "Reuters Fact Check",
            "original_rating": "True",
        }
    ]

    matched = matcher.match_reviews_to_claim(claim_sentence, candidate_reviews)
    assert len(matched) == 1
    assert matched[0]["lexical_similarity_score"] >= 0.30
    assert matched[0]["match_classification"] == "relevant_match"


def test_claim_matcher_rejects_irrelevant_result():
    """Verify that completely unrelated results are rejected."""
    matcher = ClaimMatcher(relevance_threshold=0.30, related_threshold=0.15)
    claim_sentence = "Federal Reserve lowers interest rates by 25 basis points."

    candidate_reviews = [
        {
            "claim_text_from_review": "Pop singer reveals new album cover and summer tour dates",
            "publisher_name": "Snopes",
            "original_rating": "Unproven",
        }
    ]

    matched = matcher.match_reviews_to_claim(claim_sentence, candidate_reviews)
    assert len(matched) == 1
    assert matched[0]["match_classification"] == "rejected_irrelevant"
