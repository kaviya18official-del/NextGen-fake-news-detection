"""Deterministic claim extraction service for NextGen NewsVerify.

Segments article text into sentences, scores factual density using numbers,
dates, reporting verbs, and entities, filters boilerplate, and generates
normalized search queries without altering original meaning.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

# Non-factual boilerplate patterns to exclude
BOILERPLATE_PATTERNS = [
    r"subscribe\s+to\s+our",
    r"sign\s+up\s+for",
    r"all\s+rights\s+reserved",
    r"terms\s+of\s+service",
    r"privacy\s+policy",
    r"cookie\s+policy",
    r"click\s+here\s+to",
    r"follow\s+us\s+on",
    r"share\s+this\s+article",
    r"advertisement",
    r"read\s+more:",
    r"photo\s+credit:",
    r"getty\s+images",
    r"source:\s+[a-z0-9]",
]

# Reporting and assertion verbs indicating factual claims
REPORTING_VERBS = {
    "announced", "reported", "confirmed", "stated", "claimed", "discovered",
    "admitted", "voted", "signed", "passed", "killed", "arrested", "approved",
    "published", "revealed", "denied", "concluded", "found", "tested",
    "investigated", "accused", "awarded", "unveiled", "mandated", "ruled",
}

# Date and temporal markers
TEMPORAL_PATTERN = re.compile(
    r"\b(19\d\d|20\d\d|january|february|march|april|may|june|july|august|september|"
    r"october|november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"yesterday|today|last\s+week|last\s+month|annual|fiscal\s+year)\b",
    re.IGNORECASE,
)

# Number and statistical patterns
NUMBER_PATTERN = re.compile(
    r"\b(\d+([.,]\d+)?\s*(%|percent|billion|million|thousand|hundred|trillion|dollars|\$|€|£|kg|miles|km|meters)?)\b",
    re.IGNORECASE,
)


class ClaimExtractor:
    """Extracts, filters, and ranks checkable factual claims from news text."""

    def __init__(self, max_claims: int = 8):
        self.max_claims = max_claims

    def segment_sentences(self, text: str) -> List[str]:
        """Split text into sentences safely without breaking decimals or honorifics."""
        if not text:
            return []

        # Protect common abbreviations and decimal points
        protected = text
        protected = re.sub(r"\b(Mr|Mrs|Ms|Dr|Prof|Sen|Rep|Gov|Gen|U\.S|e\.g|i\.e)\.", r"\1<DOT>", protected)
        protected = re.sub(r"(\d+)\.(\d+)", r"\1<DECIMAL>\2", protected)

        # Split on sentence terminals
        raw_sentences = re.split(r"(?<=[.!?])\s+", protected)

        sentences = []
        for s in raw_sentences:
            s_clean = s.replace("<DOT>", ".").replace("<DECIMAL>", ".").strip()
            if s_clean:
                sentences.append(s_clean)

        return sentences

    def is_valid_claim_candidate(self, sentence: str) -> bool:
        """Filter out boilerplate, questions, commands, and fragments."""
        s_lower = sentence.lower()

        # Filter length: must have at least 6 words and at least 30 characters
        words = sentence.split()
        if len(words) < 6 or len(sentence) < 30 or len(words) > 75:
            return False

        # Exclude questions
        if sentence.endswith("?") or s_lower.startswith(("why ", "how ", "what if", "should we")):
            return False

        # Exclude boilerplate phrases
        for pattern in BOILERPLATE_PATTERNS:
            if re.search(pattern, s_lower):
                return False

        # Exclude imperative social media commands
        if s_lower.startswith(("click ", "subscribe ", "share ", "follow ", "download ", "watch ")):
            return False

        return True

    def score_sentence(self, sentence: str) -> Tuple[float, str]:
        """Score sentence for checkable factual density and classify claim type."""
        words = sentence.split()
        words_lower = [w.lower().strip(".,;:\"'()") for w in words]

        has_numbers = bool(NUMBER_PATTERN.search(sentence))
        has_dates = bool(TEMPORAL_PATTERN.search(sentence))
        has_quotes = bool(re.search(r'["“\'].+?["”\']', sentence))

        verb_count = sum(1 for w in words_lower if w in REPORTING_VERBS)

        # Count capitalized words not at the beginning of sentence (proxy for named entities)
        entity_count = sum(1 for w in words[1:] if w and w[0].isupper() and w.isalpha())

        score = 0.0
        if has_numbers:
            score += 2.0
        if has_dates:
            score += 1.5
        if has_quotes:
            score += 1.0
        score += min(verb_count * 1.5, 3.0)
        score += min(entity_count * 0.5, 2.5)

        # Classify claim type
        if has_numbers and ("percent" in words_lower or "%" in sentence or "rate" in words_lower or "$" in sentence):
            claim_type = "statistical_claim"
        elif has_quotes:
            claim_type = "quotation_statement"
        elif verb_count > 0:
            claim_type = "reported_event"
        else:
            claim_type = "factual_assertion"

        return score, claim_type

    def generate_normalized_query(self, sentence: str) -> str:
        """Extract key entities and search keywords for the fact-checking API."""
        # Remove quotation marks and parentheticals
        cleaned = re.sub(r'["“\'”]', "", sentence)
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Split into tokens and remove common stopwords while keeping key terms
        common_stops = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "over", "after",
            "is", "are", "was", "were", "be", "been", "being", "have", "has",
            "had", "it", "its", "that", "this", "these", "those", "which",
        }

        tokens = [t.strip(".,;:!?()") for t in cleaned.split()]
        key_tokens = [t for t in tokens if t.lower() not in common_stops and len(t) > 1]

        # Use top 6-10 key tokens for Google Fact Check query
        query = " ".join(key_tokens[:9])
        return query if query else sentence[:100]

    def extract_claims(self, text: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract, score, filter, and return prioritized claim candidates."""
        max_c = limit or self.max_claims
        sentences = self.segment_sentences(text)

        candidates = []
        for idx, sentence in enumerate(sentences):
            if not self.is_valid_claim_candidate(sentence):
                continue

            score, claim_type = self.score_sentence(sentence)
            # Require minimum factual density score
            if score >= 1.5:
                query = self.generate_normalized_query(sentence)
                candidates.append({
                    "claim_index": len(candidates),
                    "original_sentence": sentence,
                    "normalized_query": query,
                    "claim_type": claim_type,
                    "score": round(score, 2),
                    "is_selected": True,
                })

        # Sort candidates by factual density score descending
        candidates.sort(key=lambda c: c["score"], reverse=True)

        # Cap at requested limit and re-index
        prioritized = candidates[:max_c]
        for i, c in enumerate(prioritized):
            c["claim_index"] = i

        return prioritized
