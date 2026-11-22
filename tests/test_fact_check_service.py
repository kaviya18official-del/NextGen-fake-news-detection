"""Tests for FactCheckService with mocked external HTTP calls and status handling."""

from unittest.mock import patch, MagicMock
from services.fact_check_service import FactCheckService


def test_fact_check_not_configured():
    """Verify that search returns 'not_configured' status when no API key is provided."""
    service = FactCheckService(api_key="")
    res = service.search_claim("Earth is flat")
    assert res["query_status"] == "not_configured"
    assert res["reviews"] == []


def test_fact_check_successful_found_response():
    """Verify parsing of successful Google Fact Check Tools API response."""
    service = FactCheckService(api_key="TEST_API_KEY")

    mock_api_payload = {
        "claims": [
            {
                "text": "The moon is an artificial hollow satellite.",
                "claimant": "Social Media Posts",
                "claimDate": "2024-01-15T00:00:00Z",
                "claimReview": [
                    {
                        "publisher": {"name": "PolitiFact", "site": "politifact.com"},
                        "url": "https://www.politifact.com/factchecks/2024/jan/moon-artificial/",
                        "title": "No, the moon is not an artificial satellite",
                        "textualRating": "Pants on Fire",
                        "reviewDate": "2024-01-16T12:00:00Z",
                    }
                ],
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_api_payload
        mock_get.return_value = mock_resp

        result = service.search_claim("moon artificial satellite")
        assert result["query_status"] == "found"
        assert len(result["reviews"]) == 1

        review = result["reviews"][0]
        assert review["publisher_name"] == "PolitiFact"
        assert review["original_rating"] == "Pants on Fire"
        assert "politifact.com" in review["review_url"]


def test_fact_check_no_match_response():
    """Verify that valid query with no results returns 'no_match' status rather than failure."""
    service = FactCheckService(api_key="TEST_API_KEY")

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}  # Empty claims list
        mock_get.return_value = mock_resp

        result = service.search_claim("Random uninvestigated event 2026")
        assert result["query_status"] == "no_match"
        assert result["reviews"] == []


def test_fact_check_provider_error_and_timeout():
    """Verify handling of HTTP errors and network timeouts."""
    service = FactCheckService(api_key="TEST_API_KEY")

    with patch("requests.get") as mock_get:
        # Rate limit / Quota exceeded
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        result = service.search_claim("Query")
        assert result["query_status"] == "unavailable"
        assert "rate limit" in result["message"].lower() or "quota" in result["message"].lower()
