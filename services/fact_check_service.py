"""Google Fact Check Tools API integration service for NextGen NewsVerify.

Implements query caching, timeout enforcement, schema validation, and returns
structured statuses: 'found', 'no_match', 'unavailable', or 'not_configured'.
"""

from __future__ import annotations

import os
import time
from typing import Dict, Any, List, Optional
import requests

from security.input_validator import mask_secret

GOOGLE_FACTCHECK_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class FactCheckService:
    """Interface to query Google Fact Check Tools API with caching and error isolation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: float = 5.0,
        cache_ttl_seconds: int = 3600,
    ):
        self.api_key = api_key or os.getenv("GOOGLE_FACTCHECK_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.timeout = timeout_seconds
        self.cache_ttl = cache_ttl_seconds
        # In-memory query cache: {query_str: (timestamp, results_list, status)}
        self._cache: Dict[str, Tuple[float, List[Dict[str, Any]], str]] = {}

    @property
    def is_configured(self) -> bool:
        """Return True if an API key is available."""
        return bool(self.api_key and self.api_key.strip())

    def get_masked_api_key(self) -> str:
        """Return masked key for UI display without leaking credentials."""
        return mask_secret(self.api_key)

    def search_claim(
        self,
        query: str,
        language_code: str = "en-US",
        page_size: int = 5,
    ) -> Dict[str, Any]:
        """Search Google Fact Check Tools API for previously published reviews.

        Returns:
            Dictionary with query_status ('found', 'no_match', 'unavailable', 'not_configured'),
            query, candidate_reviews list, and error message if any.
        """
        if not query or not query.strip():
            return {
                "query": query,
                "query_status": "no_match",
                "reviews": [],
                "message": "Empty search query provided.",
            }

        clean_query = query.strip()

        # Check configuration
        if not self.is_configured:
            return {
                "query": clean_query,
                "query_status": "not_configured",
                "reviews": [],
                "message": "Google Fact Check API key is not configured. Set GOOGLE_FACTCHECK_API_KEY.",
            }

        # Check Cache
        now = time.time()
        if clean_query in self._cache:
            cache_time, cached_reviews, cached_status = self._cache[clean_query]
            if (now - cache_time) < self.cache_ttl:
                return {
                    "query": clean_query,
                    "query_status": cached_status,
                    "reviews": cached_reviews,
                    "cached": True,
                }

        # Issue API request
        params = {
            "query": clean_query,
            "key": self.api_key,
            "languageCode": language_code,
            "pageSize": page_size,
        }

        try:
            resp = requests.get(
                GOOGLE_FACTCHECK_ENDPOINT,
                params=params,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        except requests.exceptions.Timeout:
            return {
                "query": clean_query,
                "query_status": "unavailable",
                "reviews": [],
                "message": f"Fact Check API request timed out after {self.timeout}s.",
            }
        except Exception as e:
            return {
                "query": clean_query,
                "query_status": "unavailable",
                "reviews": [],
                "message": f"Network or provider error: {str(e)}",
            }

        # Handle API HTTP status
        if resp.status_code == 403 or resp.status_code == 401:
            return {
                "query": clean_query,
                "query_status": "unavailable",
                "reviews": [],
                "message": f"API Authentication failed (HTTP {resp.status_code}): Invalid or restricted API key.",
            }
        elif resp.status_code == 429:
            return {
                "query": clean_query,
                "query_status": "unavailable",
                "reviews": [],
                "message": "Fact Check API rate limit or quota exceeded.",
            }
        elif resp.status_code != 200:
            return {
                "query": clean_query,
                "query_status": "unavailable",
                "reviews": [],
                "message": f"Fact Check API returned unexpected HTTP status {resp.status_code}.",
            }

        # Parse and validate response JSON
        try:
            data = resp.json()
        except Exception as e:
            return {
                "query": clean_query,
                "query_status": "unavailable",
                "reviews": [],
                "message": f"Failed to parse API JSON response: {e}",
            }

        raw_claims = data.get("claims", [])
        if not raw_claims:
            self._cache[clean_query] = (now, [], "no_match")
            return {
                "query": clean_query,
                "query_status": "no_match",
                "reviews": [],
                "message": "No matching published fact-checks were identified for this query.",
            }

        # Extract structured reviews
        extracted_reviews = []
        for c in raw_claims:
            claim_text = c.get("text", "")
            claim_date = c.get("claimDate", "")
            claimant = c.get("claimant", "")

            review_entries = c.get("claimReview", [])
            for r in review_entries:
                publisher_info = r.get("publisher", {})
                publisher_name = publisher_info.get("name", "Unknown Publisher")
                publisher_site = publisher_info.get("site", "")
                review_url = r.get("url", "")
                review_title = r.get("title", "")
                textual_rating = r.get("textualRating", "Unrated")
                review_date = r.get("reviewDate", "")

                extracted_reviews.append({
                    "claim_text_from_review": claim_text,
                    "claimant": claimant,
                    "claim_date": claim_date,
                    "publisher_name": publisher_name,
                    "publisher_site": publisher_site,
                    "original_rating": textual_rating,
                    "review_title": review_title,
                    "review_url": review_url,
                    "review_date": review_date,
                    "query_used": clean_query,
                    "query_status": "found",
                })

        status = "found" if extracted_reviews else "no_match"
        self._cache[clean_query] = (now, extracted_reviews, status)

        return {
            "query": clean_query,
            "query_status": status,
            "reviews": extracted_reviews,
        }

    def clear_cache(self) -> None:
        """Clear all in-memory query cache entries."""
        self._cache.clear()
