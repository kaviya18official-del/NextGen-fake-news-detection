"""Lexical similarity matching between extracted claims and retrieved fact-checks.

Implements token-based Jaccard overlap and character sequence matching to classify
candidate reviews as 'relevant_match', 'related_candidate', or 'rejected_irrelevant'.
"""

from __future__ import annotations

import difflib
import re
from typing import Dict, Any, List, Set

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "up", "about", "into", "over", "after", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "it", "its",
    "that", "this", "these", "those", "which", "as", "if", "than", "so", "no",
    "not", "all", "any", "both", "each", "few", "more", "most", "other", "some",
}


class ClaimMatcher:
    """Matches candidate fact-check reviews to claims using lexical and n-gram overlap."""

    def __init__(
        self,
        relevance_threshold: float = 0.30,
        related_threshold: float = 0.15,
    ):
        self.relevance_threshold = relevance_threshold
        self.related_threshold = related_threshold

    @staticmethod
    def tokenize_and_clean(text: str) -> Set[str]:
        """Convert text to a normalized set of content tokens without stopwords."""
        if not text:
            return set()
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = cleaned.split()
        return {t for t in tokens if t not in STOP_WORDS and len(t) > 1}

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Calculate combined Jaccard and character sequence similarity."""
        set_a = self.tokenize_and_clean(text_a)
        set_b = self.tokenize_and_clean(text_b)

        if not set_a or not set_b:
            return 0.0

        # Jaccard index
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        jaccard = intersection / union if union > 0 else 0.0

        # Sequence matcher ratio on normalized text
        norm_a = " ".join(sorted(set_a))
        norm_b = " ".join(sorted(set_b))
        seq_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()

        # Weighted combination favoring token overlap
        combined = 0.70 * jaccard + 0.30 * seq_ratio
        return round(float(combined), 4)

    def match_reviews_to_claim(
        self,
        claim_sentence: str,
        candidate_reviews: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compare candidate reviews against claim text and classify match quality."""
        matched_results = []

        for rev in candidate_reviews:
            review_claim_text = rev.get("claim_text_from_review", "") or rev.get("review_title", "")
            sim_score = self.compute_similarity(claim_sentence, review_claim_text)

            if sim_score >= self.relevance_threshold:
                classification = "relevant_match"
            elif sim_score >= self.related_threshold:
                classification = "related_candidate"
            else:
                classification = "rejected_irrelevant"

            enriched_review = dict(rev)
            enriched_review["lexical_similarity_score"] = sim_score
            enriched_review["match_classification"] = classification
            matched_results.append(enriched_review)

        # Sort by similarity score descending
        matched_results.sort(key=lambda r: r["lexical_similarity_score"], reverse=True)
        return matched_results
