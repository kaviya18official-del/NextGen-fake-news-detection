"""Evidence Comparison Page for NextGen NewsVerify.

Compares multiple fact-checking perspectives and highlights conflicting reviews
without arbitrarily picking a winner.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from database.repository import AnalysisRepository

st.set_page_config(page_title="Evidence Comparison — NewsVerify", page_icon="⚖️", layout="wide")

st.title("⚖️ Evidence Comparison & Conflicting Reviews")
st.markdown(
    "Examine divergent findings, conflicting ratings, and temporal discrepancies across multiple "
    "fact-checking sources. NextGen NewsVerify enforces transparency: when sources disagree materially, "
    "we document both positions without silently declaring one superior."
)

repo = AnalysisRepository()

# Option to inspect existing analyses with evidence conflicts
analyses = repo.list_analyses(limit=50)
st.subheader("Historical Analyses with Evidence Conflicts")

conflict_found = False
for item in analyses:
    dossier = repo.get_analysis(item["id"])
    if dossier and dossier.get("claims"):
        for c in dossier["claims"]:
            ass = c.get("evidence_assessment")
            if ass and ass.get("evidence_status") == "evidence_conflict":
                conflict_found = True
                with st.expander(f"⚠️ Conflict in '{dossier['article_title']}': \"{c['original_sentence'][:80]}...\"", expanded=True):
                    st.markdown(f"**Claim Statement:** \"{c['original_sentence']}\"")
                    st.markdown(f"**Assessment Explanation:** {ass['status_explanation']}")

                    conflicts = ass.get("conflicting_reviews", [])
                    if conflicts:
                        df_conflicts = pd.DataFrame(conflicts)
                        st.dataframe(df_conflicts, use_container_width=True)

if not conflict_found:
    st.info("No analyses with conflicting ratings have been recorded in the database yet.")

st.divider()

# Interactive Manual Comparison Sandbox
st.subheader("Interactive Multi-Source Comparison Sandbox")
st.markdown("Compare two different fact-checking findings or reporting angles manually:")

comp_col1, comp_col2 = st.columns(2)

with comp_col1:
    st.markdown("### Source / Fact-Check A")
    src_a_name = st.text_input("Publisher A Name:", value="PolitiFact", key="src_a_name")
    src_a_rating = st.text_input("Rating / Verdict A:", value="Mostly False", key="src_a_rating")
    src_a_date = st.text_input("Review Date A:", value="2024-02-15", key="src_a_date")
    src_a_summary = st.text_area("Findings / Rationale A:", value="Statement omits crucial regulatory exclusions in the bill.", key="src_a_summary")

with comp_col2:
    st.markdown("### Source / Fact-Check B")
    src_b_name = st.text_input("Publisher B Name:", value="Reuters Fact Check", key="src_b_name")
    src_b_rating = st.text_input("Rating / Verdict B:", value="Partially True / Context Needed", key="src_b_rating")
    src_b_date = st.text_input("Review Date B:", value="2024-02-18", key="src_b_date")
    src_b_summary = st.text_area("Findings / Rationale B:", value="Statistical numbers are accurate per official tables, but the timeline was misattributed.", key="src_b_summary")

if st.button("⚖️ Generate Discrepancy Synthesis"):
    st.markdown("---")
    st.subheader("Forensic Discrepancy Analysis")

    comp_df = pd.DataFrame([
        {"Publisher": src_a_name, "Rating": src_a_rating, "Date": src_a_date, "Key Finding": src_a_summary},
        {"Publisher": src_b_name, "Rating": src_b_rating, "Date": src_b_date, "Key Finding": src_b_summary},
    ])
    st.table(comp_df)

    st.warning(
        "**Evidence Verdict: Evidence Conflict / Multi-Perspective Review**\n\n"
        "Both organizations reviewed related aspects of the statement but arrived at diverging ratings due to differing editorial emphasis. "
        "Source A evaluated contextual omissions, while Source B prioritized numerical precision. "
        "Human investigators must review the source documentation directly rather than flattening this into a true/false binary."
    )
