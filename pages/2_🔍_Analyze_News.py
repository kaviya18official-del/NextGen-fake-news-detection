"""Analyze News Page for NextGen NewsVerify.

Primary interface for pasted text and public URL verification. Executes the 10-step
investigative pipeline, presents uncoupled ML and evidence findings, and provides exports.
"""

from __future__ import annotations

import hashlib
import time
import uuid
import streamlit as st
import plotly.express as px
import pandas as pd

from security.input_validator import validate_text_input
from services.article_extractor import ArticleExtractor
from ml.predict import NewsClassifierPredictor
from services.claim_extractor import ClaimExtractor
from services.fact_check_service import FactCheckService
from services.claim_matcher import ClaimMatcher
from services.evidence_assessor import EvidenceAssessor
from services.source_analyzer import SourceAnalyzer
from services.report_generator import ReportGenerator
from database.repository import AnalysisRepository

st.set_page_config(page_title="Analyze News — NewsVerify", page_icon="🔍", layout="wide")

st.title("🔍 Analyze News Article")
st.markdown(
    "Submit an article via pasted text or public web URL to extract checkable claims, "
    "retrieve published fact-checks, examine ML classification patterns, and receive a transparent verification dossier."
)

# Initialize components
extractor = ArticleExtractor()
predictor = NewsClassifierPredictor()
claim_extractor = ClaimExtractor()
fact_service = FactCheckService()
matcher = ClaimMatcher()
assessor = EvidenceAssessor()
repo = AnalysisRepository()

# Sidebar configuration options
st.sidebar.header("Investigation Settings")
max_claims = st.sidebar.slider("Maximum Claims to Investigate", min_value=1, max_value=10, value=5)
enable_fact_check = st.sidebar.checkbox(
    "Query Google Fact Check Tools API",
    value=fact_service.is_configured,
    help="When enabled, queries independent fact-check reviews for each extracted claim.",
)
if not fact_service.is_configured and enable_fact_check:
    st.sidebar.warning("No Fact Check API key configured. Results will reflect offline mode.")

# Check for transferred text from Screenshot OCR page
default_pasted_text = st.session_state.get("ocr_transferred_text", "")

tab_text, tab_url = st.tabs(["📝 Pasted Article Text", "🌐 Public Article URL"])

raw_text_to_analyze = None
article_metadata = {
    "title": "Manual Text Entry",
    "publisher": "User Submission",
    "domain": "Local Input",
    "author": "N/A",
    "publication_date": "N/A",
    "url": None,
    "canonical_url": None,
    "is_https": False,
}
input_type = "text"

with tab_text:
    pasted_input = st.text_area(
        "Paste Article Content (Headlines, Body, or Quotes):",
        value=default_pasted_text,
        height=220,
        placeholder="Paste full article text here (minimum 30 characters)...",
    )
    col_btn, col_clear = st.columns([1, 5])
    with col_btn:
        start_text_analysis = st.button("🚀 Analyze Pasted Text", type="primary")
    with col_clear:
        if default_pasted_text:
            if st.button("Clear OCR Transferred Text"):
                st.session_state["ocr_transferred_text"] = ""
                st.rerun()

    if start_text_analysis:
        is_valid, err_msg, cleaned = validate_text_input(pasted_input)
        if not is_valid:
            st.error(f"Input validation error: {err_msg}")
        else:
            raw_text_to_analyze = ArticleExtractor.normalize_pasted_text(cleaned)
            input_type = "text"

with tab_url:
    st.markdown("Enter a public news article URL. The system enforces strict SSRF and security protections.")
    url_input = st.text_input(
        "Article Web Address:",
        placeholder="https://apnews.com/article/example-story",
    )
    start_url_analysis = st.button("🌐 Fetch & Analyze URL", type="primary")

    if start_url_analysis:
        if not url_input or not url_input.strip():
            st.error("Please enter a valid URL.")
        else:
            with st.spinner("Safely fetching and sanitizing article content..."):
                try:
                    url_data = extractor.extract_from_url(url_input.strip())
                    raw_text_to_analyze = url_data["text"]
                    article_metadata = url_data
                    input_type = "url"
                    st.success(f"Extracted article: '{url_data['title']}' from {url_data['publisher']}")
                except Exception as e:
                    st.error(f"URL extraction failed: {str(e)}")
                    st.info("Tip: You can copy and paste the article text manually in the 'Pasted Article Text' tab.")

# Main Analysis Execution
if raw_text_to_analyze:
    start_time_all = time.perf_counter()
    analysis_id = str(uuid.uuid4())
    text_hash = hashlib.sha256(raw_text_to_analyze.encode("utf-8")).hexdigest()

    st.divider()
    st.header("📋 Verification Dossier")
    st.caption(f"Analysis ID: `{analysis_id}` | Source: `{input_type.upper()}`")

    # Step 1 & 2: Source Analysis
    source_info = SourceAnalyzer.analyze_source_metadata(article_metadata)

    with st.expander("📌 Article Provenance & Source Metadata", expanded=True):
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.markdown(f"**Publisher:** {source_info['publisher']}")
        m_col2.markdown(f"**Domain:** {source_info['domain']}")
        m_col3.markdown(f"**Byline:** {source_info['author']}")
        m_col4.markdown(f"**Published:** {source_info['publication_date']}")

        if source_info["missing_fields"]:
            st.warning("⚠️ **Missing Provenance Context:** " + " | ".join(source_info["missing_fields"]))

        st.caption(source_info["methodology_note"])

    # Step 3: Run ML Classifier
    st.subheader("1. Machine Learning Text Pattern Classification")
    ml_result = {}
    if predictor.is_available:
        try:
            ml_result = predictor.predict(raw_text_to_analyze)
            pred_class = ml_result["prediction"]
            score_val = ml_result["score"]
            score_type = ml_result["score_type"]
            uncertainty = ml_result["uncertainty"]
            latency = ml_result["processing_time_ms"]

            col_pred, col_score, col_uncert = st.columns(3)
            with col_pred:
                if pred_class.lower() == "real":
                    st.success(f"### Predicted Class: **{pred_class}**")
                else:
                    st.error(f"### Predicted Class: **{pred_class}**")
            with col_score:
                st.metric("Model Confidence Score", f"{score_val:.4f}", help=f"Score Type: {score_type}")
            with col_uncert:
                st.metric("Statistical Uncertainty", uncertainty)

            # Feature Attribution Visualizer
            explanation = ml_result.get("explanation", {})
            if explanation.get("available") and explanation.get("top_features"):
                st.markdown("**Influential Learned Vocabulary Features in this Article:**")
                df_feat = pd.DataFrame(explanation["top_features"])
                fig_feat = px.bar(
                    df_feat,
                    x="contribution",
                    y="word",
                    orientation="h",
                    color="pushed_towards",
                    title="Vocabulary Contribution to Model Score (Positive vs Negative Direction)",
                    labels={"contribution": "Linear Score Contribution", "word": "Word Feature"},
                    color_discrete_map={"Real": "#38A169", "Fake": "#E53E3E"},
                )
                fig_feat.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_feat, use_container_width=True)

            st.caption(f"ℹ️ {ml_result['limitations']}")
        except Exception as e:
            st.error(f"ML Classifier error: {e}")
    else:
        st.warning(
            "⚠️ ML Model is not trained. Run: `python -m ml.train --data data/news_sample.csv` to enable inference."
        )

    # Step 4: Extract checkable claims
    st.subheader("2. Checkable Claims Extraction")
    extracted_claims = claim_extractor.extract_claims(raw_text_to_analyze, limit=max_claims)

    if not extracted_claims:
        st.info("No distinct factual claims meeting the criteria were identified in the text. You can verify individual custom claims on the 'Claim Verification' page.")
    else:
        st.markdown(f"Extracted **{len(extracted_claims)}** prioritized checkable factual assertions:")

        analyzed_claims_list = []
        assessments_list = []

        for c in extracted_claims:
            claim_idx = c["claim_index"]
            sentence = c["original_sentence"]
            query = c["normalized_query"]
            claim_type = c["claim_type"].replace("_", " ").title()

            st.markdown(f"---")
            st.markdown(f"#### Claim #{claim_idx + 1} — *{claim_type}*")
            st.info(f"**Statement:** \"{sentence}\"")
            st.caption(f"Generated Search Query: `{query}` | Factual Density Score: {c['score']}")

            # Step 5 & 6: Search & Match Fact-Checks
            matched_reviews = []
            ev_assessment = {}

            if enable_fact_check:
                search_res = fact_service.search_claim(query)
                query_status = search_res.get("query_status", "unavailable")
                candidate_reviews = search_res.get("reviews", [])

                matched_reviews = matcher.match_reviews_to_claim(sentence, candidate_reviews)
                ev_assessment = assessor.assess_claim_evidence(query_status, matched_reviews)
            else:
                query_status = "not_configured"
                ev_assessment = assessor.assess_claim_evidence(query_status, [])

            c["fact_checks"] = matched_reviews
            ev_assessment["claim_index"] = claim_idx

            analyzed_claims_list.append(c)
            assessments_list.append(ev_assessment)

            # Display Evidence Assessment Card
            ev_status = ev_assessment["evidence_status"]
            ev_badge_color = {
                "prior_fact_check_found": "blue",
                "no_matching_fact_check": "gray",
                "insufficient_evidence": "orange",
                "evidence_conflict": "red",
                "lookup_unavailable": "gray",
            }.get(ev_status, "gray")

            status_display = ev_status.replace("_", " ").upper()
            if ev_status == "prior_fact_check_found":
                st.success(f"**Evidence Status: {status_display}**\n\n{ev_assessment['status_explanation']}")
            elif ev_status == "evidence_conflict":
                st.error(f"**Evidence Status: {status_display}**\n\n{ev_assessment['status_explanation']}")
            elif ev_status == "insufficient_evidence":
                st.warning(f"**Evidence Status: {status_display}**\n\n{ev_assessment['status_explanation']}")
            else:
                st.info(f"**Evidence Status: {status_display}**\n\n{ev_assessment['status_explanation']}")

            # Display Matched Reviews
            relevant = [r for r in matched_reviews if r.get("match_classification") in ("relevant_match", "related_candidate")]
            if relevant:
                st.markdown("**Indexed Published Fact-Checks:**")
                for r in relevant:
                    sim_pct = int(r["lexical_similarity_score"] * 100)
                    r_col1, r_col2, r_col3 = st.columns([3, 2, 2])
                    r_col1.markdown(f"**[{r['publisher_name']}]({r['review_url']})** — Rating: `{r['original_rating']}`")
                    r_col2.markdown(f"Match: `{r['match_classification']}` ({sim_pct}%)")
                    r_col3.markdown(f"Date: `{r['review_date'] or 'N/A'}`")

        # Step 8 & 9: Persist Analysis Record
        elapsed_total = round((time.perf_counter() - start_time_all) * 1000, 2)
        analysis_record = {
            "id": analysis_id,
            "input_type": input_type,
            "article_title": article_metadata.get("title"),
            "article_url": article_metadata.get("url"),
            "article_publisher": article_metadata.get("publisher"),
            "publication_date": article_metadata.get("publication_date"),
            "article_preview": raw_text_to_analyze[:400],
            "article_text_hash": text_hash,
            "model_version": ml_result.get("model_version"),
            "ml_prediction": ml_result.get("prediction"),
            "ml_score": ml_result.get("score"),
            "ml_score_type": ml_result.get("score_type"),
            "ml_uncertainty": ml_result.get("uncertainty"),
            "ml_explanation": ml_result.get("explanation"),
            "processing_time_ms": elapsed_total,
            "status": "completed",
        }

        try:
            repo.save_analysis(analysis_record, analyzed_claims_list, assessments_list)
            st.success(f"✅ Full analysis dossier saved to local SQLite database (ID: `{analysis_id}`).")
        except Exception as e:
            st.warning(f"Could not save record to database: {e}")

        # Step 10: Report Downloads
        st.divider()
        st.subheader("📥 Export Verification Reports")
        dossier_data = repo.get_analysis(analysis_id) or analysis_record

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            json_str = ReportGenerator.generate_json_report(dossier_data)
            st.download_button(
                label="📄 Download JSON Dossier",
                data=json_str,
                file_name=f"newsverify_{analysis_id}.json",
                mime="application/json",
            )
        with d_col2:
            try:
                pdf_bytes = ReportGenerator.generate_pdf_report(dossier_data)
                st.download_button(
                    label="📕 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"newsverify_{analysis_id}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
