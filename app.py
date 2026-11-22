"""NextGen NewsVerify — AI-Powered News Analysis and Fact-Checking Assistant.

Main entry point and overview portal for the Streamlit application.
"""

from __future__ import annotations

import os
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

import streamlit as st
from database.repository import AnalysisRepository
from ml.predict import NewsClassifierPredictor
from services.fact_check_service import FactCheckService

st.set_page_config(
    page_title="NextGen NewsVerify",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ NextGen NewsVerify")
st.subheader("AI-Powered News Analysis & Multi-Source Fact-Checking Assistant")

st.markdown(
    """
    **NextGen NewsVerify** is an investigative decision-support assistant designed for journalists,
    researchers, and citizens. It does **not** claim to be an automated arbiter of truth. Instead,
    it systematically answers **five distinct questions** without collapsing them into an arbitrary score:
    """
)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.info("🤖 **1. ML Pattern**\n\nWhat stylistic and lexical patterns does the model detect compared to trained distributions?")
with col2:
    st.info("🔍 **2. Checkable Claims**\n\nWhich specific statements in the article contain verifiable numbers, dates, or assertions?")
with col3:
    st.info("📰 **3. Prior Fact-Checks**\n\nHave independent fact-checking organizations previously investigated these claims?")
with col4:
    st.info("⚖️ **4. Evidence Match**\n\nWhat supporting, conflicting, or inconclusive published evidence is available?")
with col5:
    st.info("📋 **5. Responsible Synthesis**\n\nWhat can be responsibly concluded, and what remains unknown or unresolved?")

st.divider()

# System Status & Quick Stats
repo = AnalysisRepository()
stats = repo.get_statistics()
predictor = NewsClassifierPredictor()
fact_service = FactCheckService()

st.subheader("System Architecture & Readiness")
stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)

with stat_c1:
    st.metric("Total Analyses Conducted", stats.get("total_analyses", 0))

with stat_c2:
    st.metric("Verifiable Claims Indexed", stats.get("total_claims", 0))

with stat_c3:
    if predictor.is_available:
        model_name = predictor.metadata.get("model_type", "Active")
        st.success(f"ML Classifier: **{model_name}**")
    else:
        st.warning("ML Classifier: **Untrained** (Run `ml.train`)")

with stat_c4:
    if fact_service.is_configured:
        st.success(f"Fact-Check API: **Configured** ({fact_service.get_masked_api_key()})")
    else:
        st.info("Fact-Check API: **Unconfigured** (Offline Mode)")

st.divider()

st.subheader("Navigation Quick Guide")
nav_col1, nav_col2 = st.columns(2)

with nav_col1:
    st.markdown(
        """
        - **[📊 Dashboard](Dashboard)**: Live metrics, evidence status distribution, and recent analyses.
        - **[🔍 Analyze News](Analyze_News)**: Submit article text or public URL for complete 10-step investigation.
        - **[🖼️ Screenshot Analysis](Screenshot_Analysis)**: OCR extraction and editable transcription for images.
        - **[🎯 Claim Verification](Claim_Verification)**: Deep-dive into specific extracted or custom claims.
        """
    )

with nav_col2:
    st.markdown(
        """
        - **[⚖️ Evidence Comparison](Evidence_Comparison)**: Inspect contradictory reviews and publisher divergences.
        - **[📜 Analysis History](Analysis_History)**: Review persisted dossiers, filter by status, and export PDF/JSON.
        - **[📈 Model Performance](Model_Performance)**: View held-out test benchmarks and interactive confusion matrices.
        - **[⚙️ Settings](Settings)**: Configure Google Fact Check API, inspect data retention, and audit security guards.
        """
    )

st.caption("NextGen NewsVerify • Built with Python, Streamlit, Scikit-learn, and ReportLab • Free from ungrounded truth percentages.")
