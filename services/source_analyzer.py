"""Source and publication metadata analyzer for NextGen NewsVerify.

Extracts domain, author, timestamp, canonical URL, and HTTPS status.
Explicitly identifies missing metadata and contextual risk factors without
inventing arbitrary reputation scores.
"""

from __future__ import annotations

from typing import Dict, Any, List
from urllib.parse import urlparse


class SourceAnalyzer:
    """Analyzes article provenance, publisher metadata, and identifies missing context."""

    @staticmethod
    def analyze_source_metadata(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Examine metadata fields and generate transparent contextual observations."""
        url = article_data.get("url") or article_data.get("canonical_url")
        publisher = article_data.get("publisher")
        domain = article_data.get("domain")
        author = article_data.get("author")
        pub_date = article_data.get("publication_date")
        is_https = article_data.get("is_https", False)

        if url and not domain:
            try:
                domain = urlparse(url).netloc.lower().lstrip("www.")
            except Exception:
                domain = None

        # Detect missing metadata
        missing_fields: List[str] = []
        if not author:
            missing_fields.append("Author attribution (byline) is missing.")
        if not pub_date:
            missing_fields.append("Explicit publication date or timestamp is missing.")
        if not publisher:
            missing_fields.append("Publisher or organization meta-tag is missing.")
        if not is_https and url and url.startswith("http://"):
            missing_fields.append("Connection does not use HTTPS encryption.")

        # Disclaimers and principles
        observations: List[str] = []
        if missing_fields:
            observations.append(
                f"Noticeable missing metadata ({len(missing_fields)} items detected). "
                "While not proof of inaccuracies, missing bylines and publication dates reduce traceability."
            )
        else:
            observations.append(
                "Complete metadata extracted: byline, publication timestamp, and publisher identity are present."
            )

        if domain:
            observations.append(f"Content published on domain: '{domain}'.")

        disclaimer = (
            "Source metadata is contextual intelligence, NOT proof of truth or falsehood. "
            "NextGen NewsVerify never generates artificial domain reliability percentages."
        )

        return {
            "domain": domain or "Unknown Domain",
            "publisher": publisher or "Unspecified Publisher",
            "author": author or "Uncredited / Unknown Author",
            "publication_date": pub_date or "Date not specified",
            "canonical_url": article_data.get("canonical_url") or url,
            "is_https": is_https,
            "missing_fields": missing_fields,
            "observations": observations,
            "methodology_note": disclaimer,
        }
