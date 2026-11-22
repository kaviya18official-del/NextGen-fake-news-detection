"""Analysis History Page for NextGen NewsVerify.

Browse, search, inspect, export, and delete persisted investigation dossiers.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.repository import AnalysisRepository
from services.report_generator import ReportGenerator

st.set_page_config(page_title="Analysis History — NewsVerify", page_icon="📜", layout="wide")

st.title("📜 Analysis History & Dossier Archive")
st.markdown("Search, inspect, export, or prune historical verification records stored in the SQLite database.")

repo = AnalysisRepository()

# Filter & Search Toolbar
col_search, col_status, col_purge = st.columns([3, 2, 2])

with col_search:
    search_term = st.text_input("🔍 Search History (Title, URL, or Content):", placeholder="e.g. Federal Reserve, NASA...")

with col_status:
    status_filter = st.selectbox("Filter by Status:", options=["All", "completed", "partial", "failed"])
    filter_val = None if status_filter == "All" else status_filter

with col_purge:
    st.markdown("**Data Retention**")
    days_to_keep = st.number_input("Purge older than (days):", min_value=1, max_value=365, value=30)
    if st.button("🗑️ Purge Expired Records"):
        count = repo.delete_older_than(days_to_keep)
        st.success(f"Purged {count} records older than {days_to_keep} days.")
        st.rerun()

st.divider()

# Load records
records = repo.list_analyses(limit=100, search_query=search_term, status_filter=filter_val)

if not records:
    st.info("No matching analysis records found in the archive.")
else:
    st.markdown(f"Found **{len(records)}** archived dossiers:")

    for item in records:
        a_id = item["id"]
        title = item["article_title"] or "Untitled Article"
        pred = item["ml_prediction"] or "N/A"
        date_str = item["created_at"] or "N/A"
        inp_type = item["input_type"].upper()

        with st.expander(f"📁 {title} | {inp_type} | ML: {pred} | {date_str[:10]}", expanded=False):
            dossier = repo.get_analysis(a_id)
            if not dossier:
                st.error("Could not load details for this analysis.")
                continue

            info_col1, info_col2, info_col3 = st.columns(3)
            info_col1.markdown(f"**Analysis ID:** `{a_id}`")
            info_col1.markdown(f"**Source URL:** {dossier.get('article_url') or 'N/A'}")
            info_col2.markdown(f"**ML Prediction:** `{dossier.get('ml_prediction')}` ({dossier.get('ml_score')})")
            info_col2.markdown(f"**Uncertainty:** {dossier.get('ml_uncertainty')}")
            info_col3.markdown(f"**Processed in:** {dossier.get('processing_time_ms', 0):.2f} ms")
            info_col3.markdown(f"**Status:** `{dossier.get('status')}`")

            st.markdown(f"**Article Preview:**\n> {dossier.get('article_preview') or 'No preview recorded.'}")

            # Claims summary
            claims = dossier.get("claims", [])
            st.markdown(f"**Investigated Claims ({len(claims)}):**")
            for c in claims:
                ass = c.get("evidence_assessment") or {}
                status_label = ass.get("evidence_status", "N/A").replace("_", " ").upper()
                st.markdown(f"- **Claim #{c['claim_index'] + 1}:** \"{c['original_sentence']}\" — `[{status_label}]`")

            # Actions: Export & Delete
            btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 2])
            with btn_col1:
                json_str = ReportGenerator.generate_json_report(dossier)
                st.download_button(
                    label="📄 Download JSON",
                    data=json_str,
                    file_name=f"newsverify_{a_id}.json",
                    mime="application/json",
                    key=f"json_{a_id}",
                )
            with btn_col2:
                try:
                    pdf_bytes = ReportGenerator.generate_pdf_report(dossier)
                    st.download_button(
                        label="📕 Download PDF",
                        data=pdf_bytes,
                        file_name=f"newsverify_{a_id}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{a_id}",
                    )
                except Exception as e:
                    st.caption(f"PDF export error: {e}")
            with btn_col3:
                if st.button("🗑️ Delete Dossier", key=f"del_{a_id}", type="secondary"):
                    repo.delete_analysis(a_id)
                    st.success("Dossier deleted.")
                    st.rerun()
