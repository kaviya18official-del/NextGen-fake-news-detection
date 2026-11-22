"""Dashboard Page for NextGen NewsVerify.

Displays real-time analysis volume, verifiable claim counts, evidence status
distributions, and recent investigation records.
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import pandas as pd

from database.repository import AnalysisRepository
from ml.predict import NewsClassifierPredictor

st.set_page_config(page_title="Dashboard — NewsVerify", page_icon="📊", layout="wide")

st.title("📊 NewsVerify Dashboard")
st.markdown("Overview of verification activity, evidence distribution, and system performance.")

repo = AnalysisRepository()
stats = repo.get_statistics()
predictor = NewsClassifierPredictor()

# Top metric cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Analyses", stats.get("total_analyses", 0))
with c2:
    st.metric("Claims Evaluated", stats.get("total_claims", 0))
with c3:
    st.metric("External Reviews Indexed", stats.get("total_reviews", 0))
with c4:
    active_model = predictor.metadata.get("model_type", "None") if predictor.is_available else "Not Trained"
    st.metric("Active Classifier", active_model)

st.divider()

# Charts row
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Evidence Assessment Distribution")
    ev_breakdown = stats.get("evidence_status_breakdown", {})
    if ev_breakdown:
        df_ev = pd.DataFrame(list(ev_breakdown.items()), columns=["Status", "Count"])
        df_ev["Status_Label"] = df_ev["Status"].str.replace("_", " ").str.title()
        fig_ev = px.pie(
            df_ev,
            names="Status_Label",
            values="Count",
            color="Status_Label",
            hole=0.4,
            color_discrete_map={
                "Prior Fact Check Found": "#3182CE",
                "No Matching Fact Check": "#718096",
                "Insufficient Evidence": "#ED8936",
                "Evidence Conflict": "#E53E3E",
                "Lookup Unavailable": "#A0AEC0",
            },
        )
        fig_ev.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_ev, use_container_width=True)
    else:
        st.info("No claim evidence assessments recorded yet. Run an analysis in 'Analyze News'.")

with col_right:
    st.subheader("ML Auxiliary Prediction Distribution")
    ml_breakdown = stats.get("ml_prediction_breakdown", {})
    if ml_breakdown:
        df_ml = pd.DataFrame(list(ml_breakdown.items()), columns=["Prediction", "Count"])
        fig_ml = px.bar(
            df_ml,
            x="Prediction",
            y="Count",
            color="Prediction",
            text="Count",
            color_discrete_map={"Real": "#38A169", "Fake": "#E53E3E"},
        )
        fig_ml.update_layout(margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Class", yaxis_title="Analyses")
        st.plotly_chart(fig_ml, use_container_width=True)
    else:
        st.info("No ML predictions stored yet.")

st.divider()

# Recent Analyses Table
st.subheader("Recent Verification Dossiers")
recent_items = repo.list_analyses(limit=10)

if recent_items:
    df_recent = pd.DataFrame(recent_items)
    display_df = df_recent[["id", "input_type", "article_title", "ml_prediction", "status", "created_at"]].copy()
    display_df.columns = ["Analysis ID", "Type", "Title / Source", "ML Prediction", "Status", "Date (UTC)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No historical analyses found. Head to 'Analyze News' to analyze your first article.")
