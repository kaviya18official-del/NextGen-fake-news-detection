"""Claim Verification Page for NextGen NewsVerify.

Enables targeted investigation of standalone claims with real-time Fact Check API
queries, lexical similarity calibration, and evidence assessment.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from services.fact_check_service import FactCheckService
from services.claim_matcher import ClaimMatcher
from services.evidence_assessor import EvidenceAssessor

st.set_page_config(page_title="Claim Verification — NewsVerify", page_icon="🎯", layout="wide")

st.title("🎯 Targeted Claim Verification")
st.markdown(
    "Investigate a specific factual assertion or statement. Search independent fact-checking databases, "
    "adjust lexical matching sensitivity, and inspect original publisher verdicts."
)

fact_service = FactCheckService()
matcher = ClaimMatcher()
assessor = EvidenceAssessor()

# Configuration Sidebar
st.sidebar.header("Matching Thresholds")
rel_threshold = st.sidebar.slider(
    "Relevance Threshold (Jaccard + Sequence)",
    min_value=0.10,
    max_value=0.70,
    value=0.30,
    step=0.05,
    help="Minimum lexical similarity required to treat a review as a relevant match.",
)
related_threshold = st.sidebar.slider(
    "Related Candidate Threshold",
    min_value=0.05,
    max_value=0.30,
    value=0.15,
    step=0.05,
    help="Threshold below which candidate results are rejected as completely irrelevant.",
)

matcher.relevance_threshold = rel_threshold
matcher.related_threshold = related_threshold

# Input Form
claim_input = st.text_input(
    "Enter Claim Statement to Investigate:",
    placeholder="e.g. World Health Organization approved the new R21 malaria vaccine for infants.",
)

search_btn = st.button("🔍 Search Fact-Checks", type="primary")

if search_btn and claim_input:
    clean_claim = claim_input.strip()
    if len(clean_claim) < 10:
        st.error("Please enter a claim with at least 10 characters.")
    else:
        with st.spinner("Searching Google Fact Check Tools API..."):
            res = fact_service.search_claim(clean_claim)
            status = res["query_status"]
            reviews = res.get("reviews", [])

        st.subheader("Investigation Results")

        # Handle lookup statuses
        if status == "not_configured":
            st.warning("⚠️ Google Fact Check Tools API is not configured. Add your API key in the 'Settings' page or `.env` file.")
        elif status == "unavailable":
            st.error(f"⚠️ Provider error or service unavailable: {res.get('message', 'Network failure')}")
        elif status == "no_match" or not reviews:
            st.info("ℹ️ **No matching fact-checks found in indexed databases.**\n\n*Note: This does not prove whether the claim is true or false. Unreported or emerging events may not have been fact-checked yet.*")
        else:
            # Match candidates
            matched = matcher.match_reviews_to_claim(clean_claim, reviews)
            assessment = assessor.assess_claim_evidence(status, matched)

            # Display Evidence Verdict Card
            ev_status = assessment["evidence_status"]
            if ev_status == "prior_fact_check_found":
                st.success(f"**Evidence Status: PRIOR FACT-CHECK FOUND**\n\n{assessment['status_explanation']}")
            elif ev_status == "evidence_conflict":
                st.error(f"**Evidence Status: EVIDENCE CONFLICT**\n\n{assessment['status_explanation']}")
            elif ev_status == "insufficient_evidence":
                st.warning(f"**Evidence Status: INSUFFICIENT EVIDENCE**\n\n{assessment['status_explanation']}")
            else:
                st.info(f"**Evidence Status: {ev_status.upper()}**\n\n{assessment['status_explanation']}")

            st.divider()
            st.subheader(f"Retrieved Reviews ({len(matched)} Candidates)")

            for idx, r in enumerate(matched, start=1):
                sim_pct = int(r["lexical_similarity_score"] * 100)
                classification = r["match_classification"]

                with st.expander(f"Review #{idx}: {r['publisher_name']} — Rating: '{r['original_rating']}' (Match: {sim_pct}%)", expanded=(classification == "relevant_match")):
                    c_col1, c_col2 = st.columns([3, 1])
                    with c_col1:
                        st.markdown(f"**Original Claim Reviewed:** \"{r['claim_text_from_review']}\"")
                        st.markdown(f"**Publisher:** [{r['publisher_name']}]({r['review_url']})")
                        st.markdown(f"**Publisher Rating:** `{r['original_rating']}`")
                        st.markdown(f"**Publication Date:** {r['review_date'] or 'N/A'}")
                    with c_col2:
                        if classification == "relevant_match":
                            st.success(f"Status: **Relevant**\n\nScore: {sim_pct}%")
                        elif classification == "related_candidate":
                            st.warning(f"Status: **Related**\n\nScore: {sim_pct}%")
                        else:
                            st.error(f"Status: **Irrelevant**\n\nScore: {sim_pct}%")
