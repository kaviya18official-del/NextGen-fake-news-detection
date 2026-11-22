"""Settings & System Health Page for NextGen NewsVerify.

Manages API configurations, privacy safeguards, security audit status,
cache purging, and methodology disclosures.
"""

from __future__ import annotations

import os
import streamlit as st

from services.fact_check_service import FactCheckService
from database.connection import DB_PATH
from database.repository import AnalysisRepository
from security.input_validator import mask_secret

st.set_page_config(page_title="Settings — NewsVerify", page_icon="⚙️", layout="wide")

st.title("⚙️ System Settings & Health")
st.markdown("Inspect API connectivity, manage local data retention, audit security controls, and review methodology guidelines.")

fact_service = FactCheckService()
repo = AnalysisRepository()

# 1. API Configuration
st.subheader("1. External Fact-Checking Provider")
st.markdown("Configure the **Google Fact Check Tools API** to retrieve published verification records.")

current_key = os.getenv("GOOGLE_FACTCHECK_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
masked_display = mask_secret(current_key) if current_key else "<Not Set>"

col_k1, col_k2 = st.columns([2, 1])
with col_k1:
    st.text_input("Active API Key (Environment Variable `GOOGLE_FACTCHECK_API_KEY`):", value=masked_display, disabled=True)
with col_k2:
    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("🔌 Test API Connectivity"):
        if not fact_service.is_configured:
            st.warning("Cannot test: No API key is configured. Add `GOOGLE_FACTCHECK_API_KEY` to your `.env` file.")
        else:
            with st.spinner("Pinging Fact Check Tools API with probe query..."):
                res = fact_service.search_claim("test probe query")
                if res["query_status"] in ("found", "no_match"):
                    st.success(f"API Connection Successful! Status: `{res['query_status']}`")
                else:
                    st.error(f"API Connection Failed: {res.get('message')}")

st.caption("To configure or update the key, create a `.env` file in the project root: `GOOGLE_FACTCHECK_API_KEY=your_key_here`.")

st.divider()

# 2. Database & Data Retention
st.subheader("2. Data Storage & Privacy Retention")
st.markdown(f"**SQLite Database Path:** `{DB_PATH}`")

c_ret1, c_ret2 = st.columns(2)
with c_ret1:
    st.markdown("**Local Data Retention**")
    retention_days = st.number_input("Configured Retention Threshold (Days):", min_value=1, max_value=365, value=30)
    if st.button("🧹 Purge Records Older Than Threshold"):
        purged = repo.delete_older_than(retention_days)
        st.success(f"Successfully deleted {purged} records exceeding {retention_days} days.")

with c_ret2:
    st.markdown("**Query Cache**")
    st.markdown("Fact-check API results are cached in memory (1 hour TTL) to minimize quota consumption.")
    if st.button("🔄 Clear In-Memory Fact-Check Cache"):
        fact_service.clear_cache()
        st.success("Fact-check query cache cleared.")

st.divider()

# 3. Security Hardening Audit
st.subheader("3. Security Hardening & SSRF Protection")
st.markdown("NextGen NewsVerify enforces layered defensive security controls:")

sec_data = [
    {"Control": "SSRF IP Blocking", "Status": "Active", "Description": "Rejects loopback (127.0.0.0/8), private (10/8, 172.16/12, 192.168/16), and link-local ranges."},
    {"Control": "Cloud Metadata Guard", "Status": "Active", "Description": "Blocks AWS/GCP/Azure endpoints (169.254.169.254, metadata.google.internal)."},
    {"Control": "Redirect Re-Validation", "Status": "Active", "Description": "Inspects each HTTP 3xx redirect destination to prevent rebinding."},
    {"Control": "Port Whitelist", "Status": "Active", "Description": "Restricted strictly to standard web ports (80, 443, 8080)."},
    {"Control": "HTML Content Sanitizer", "Status": "Active", "Description": "Decomposes script, iframe, object, embed, and inline JS event handlers."},
    {"Control": "Image Upload Validation", "Status": "Active", "Description": "Verifies magic bytes, PIL header decoding, and caps uploads at 10MB."},
    {"Control": "Path Traversal Protection", "Status": "Active", "Description": "Neutralizes relative path characters in filenames."},
    {"Control": "SQL Injection Defense", "Status": "Active", "Description": "Uses SQLAlchemy ORM with parameterized queries and SQLite foreign-key pragma."},
]
st.table(sec_data)

st.divider()

# 4. Core Methodology & Responsible Use
st.subheader("4. Investigative Assistant Principles")
st.markdown(
    """
    1. **Not a Truth Detector**: This tool assists verification workflows; it does not replace human editorial judgement.
    2. **Five Distinct Inquiries**: We deliberately avoid synthesizing ML classifications and fact-checks into a single truth percentage.
    3. **Uncertainty Transparency**: When evidence is conflicting, incomplete, or unavailable, the system states so explicitly.
    4. **Source Traceability**: Every retrieved review includes the publisher's original rating, publication date, and direct link.
    """
)
