"""Tests for deterministic claim extraction and ranking in services/claim_extractor.py."""

from services.claim_extractor import ClaimExtractor


def test_claim_extractor_factual_statements():
    """Verify that sentences containing numbers, dates, and reporting verbs are extracted."""
    text = (
        "The Federal Reserve announced on Wednesday that benchmark interest rates will be lowered by 50 basis points. "
        "Economic analysts confirmed that consumer spending rose 2.4 percent in October. "
        "Do you want to know what this means for your mortgage? "
        "Click here to subscribe to our daily finance newsletter! "
        "The President signed the new infrastructure accord into law yesterday afternoon."
    )

    extractor = ClaimExtractor(max_claims=5)
    claims = extractor.extract_claims(text)

    # Questions and subscription boilerplate must be excluded
    sentences = [c["original_sentence"] for c in claims]
    assert any("Federal Reserve announced" in s for s in sentences)
    assert any("consumer spending rose 2.4 percent" in s for s in sentences)
    assert any("President signed" in s for s in sentences)

    assert not any("Do you want to know" in s for s in sentences)
    assert not any("Click here to subscribe" in s for s in sentences)


def test_claim_extractor_normalized_query():
    """Verify normalized search queries remove conversational stop words."""
    extractor = ClaimExtractor()
    sentence = "The Centers for Disease Control and Prevention confirmed that influenza cases increased by 15 percent last week."
    query = extractor.generate_normalized_query(sentence)

    assert "Centers" in query
    assert "Disease" in query
    assert "influenza" in query or "increased" in query
    # Common stops like "and", "the" should be filtered out
    assert " the " not in f" {query.lower()} "


def test_claim_extractor_empty_and_short():
    """Verify empty or fragment text returns an empty list without crashing."""
    extractor = ClaimExtractor()
    assert extractor.extract_claims("") == []
    assert extractor.extract_claims("Short. Bye.") == []
