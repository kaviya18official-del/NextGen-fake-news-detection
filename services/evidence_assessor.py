"""Deterministic evidence assessment service for NextGen NewsVerify.

Consumes matched fact-check reviews (independent of ML predictions) and determines
one of five verifiable statuses:
1. prior_fact_check_found
2. no_matching_fact_check
3. insufficient_evidence
4. evidence_conflict
5. lookup_unavailable
"""

from __future__ import annotations

from typing import Dict, Any, List

# Keywords indicating a debunked / false rating
RATING_FALSE_KEYWORDS = {"false", "pants on fire", "fake", "incorrect", "debunked", "misleading", "distorted", "hoax", "unproven"}
# Keywords indicating a confirmed / true rating
RATING_TRUE_KEYWORDS = {"true", "correct", "accurate", "verified", "mostly true", "confirmed"}


class EvidenceAssessor:
    """Evaluates the state of external fact-checking evidence without relying on ML scores."""

    @staticmethod
    def classify_rating_sentiment(rating_str: str | None) -> str:
        """Classify a publisher's raw rating into 'false_leaning', 'true_leaning', or 'unclear'."""
        if not rating_str:
            return "unclear"
        r_lower = rating_str.lower().strip()
        for kw in RATING_FALSE_KEYWORDS:
            if kw in r_lower:
                return "false_leaning"
        for kw in RATING_TRUE_KEYWORDS:
            if kw in r_lower:
                return "true_leaning"
        return "unclear"

    def assess_claim_evidence(
        self,
        query_status: str,
        matched_reviews: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Produce an evidence status and explanation for a single claim."""
        # 1. Lookup unavailable or not configured
        if query_status in ("unavailable", "not_configured"):
            return {
                "evidence_status": "lookup_unavailable",
                "status_explanation": (
                    "External fact-check lookup could not be completed due to missing API "
                    "credentials or a provider connectivity issue. The machine learning "
                    "prediction remains available as an auxiliary signal."
                ),
                "conflicting_reviews": [],
                "limitations": "External fact-check verification was unavailable for this claim.",
            }

        # 2. No matching fact-check returned by provider
        if query_status == "no_match" or not matched_reviews:
            return {
                "evidence_status": "no_matching_fact_check",
                "status_explanation": (
                    "No matching fact-check was found in the sources searched. "
                    "This does not establish whether the claim is true or false."
                ),
                "conflicting_reviews": [],
                "limitations": "Lack of a prior fact-check does not prove accuracy.",
            }

        # Filter candidate reviews by relevance classification
        relevant_matches = [
            r for r in matched_reviews if r.get("match_classification") == "relevant_match"
        ]
        related_candidates = [
            r for r in matched_reviews if r.get("match_classification") == "related_candidate"
        ]

        # 3. All reviews were rejected as irrelevant
        if not relevant_matches and not related_candidates:
            return {
                "evidence_status": "insufficient_evidence",
                "status_explanation": (
                    "The search engine returned candidate results, but lexical matching determined "
                    "that none of them closely correspond to this specific factual statement. "
                    "Available evidence is insufficient to assess this claim."
                ),
                "conflicting_reviews": [],
                "limitations": "Returned articles did not meet the required relevance similarity threshold.",
            }

        # 4. Only weakly related candidates found
        if not relevant_matches and related_candidates:
            return {
                "evidence_status": "insufficient_evidence",
                "status_explanation": (
                    "Only weakly related reviews were located (similarity below relevant threshold). "
                    "These articles discuss related topics but do not directly evaluate this exact claim."
                ),
                "conflicting_reviews": [],
                "limitations": "Manual user inspection of related source links is recommended.",
            }

        # 5. Check for conflicting verdicts among relevant matches
        sentiments = set()
        conflicts = []
        for r in relevant_matches:
            sentiment = self.classify_rating_sentiment(r.get("original_rating"))
            if sentiment in ("false_leaning", "true_leaning"):
                sentiments.add(sentiment)
                conflicts.append({
                    "publisher": r.get("publisher_name"),
                    "rating": r.get("original_rating"),
                    "date": r.get("review_date"),
                    "url": r.get("review_url"),
                    "sentiment": sentiment,
                })

        if "false_leaning" in sentiments and "true_leaning" in sentiments:
            return {
                "evidence_status": "evidence_conflict",
                "status_explanation": (
                    "Multiple independent fact-checking organizations have published conflicting "
                    "or diverging ratings for this claim. Both perspectives are presented for inspection "
                    "without arbitrarily selecting a winner."
                ),
                "conflicting_reviews": conflicts,
                "limitations": "Conflicting publisher ratings require direct editorial review.",
            }

        # 6. Prior fact check found
        top_review = relevant_matches[0]
        publisher = top_review.get("publisher_name", "An independent organization")
        rating = top_review.get("original_rating", "Unrated")

        return {
            "evidence_status": "prior_fact_check_found",
            "status_explanation": (
                f"Prior published fact-check identified from {publisher} with an original rating of "
                f"'{rating}'. Review URL and publication details are provided for verification."
            ),
            "conflicting_reviews": [],
            "limitations": "Publisher ratings reflect external investigative findings at their date of publication.",
        }
