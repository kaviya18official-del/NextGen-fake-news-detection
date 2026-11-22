"""Model Performance Page for NextGen NewsVerify.

Presents empirical evaluation benchmarks from held-out test splits,
multi-model validation comparisons, interactive confusion matrices, and calibration curves.
"""

from __future__ import annotations

import json
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from database.repository import AnalysisRepository

st.set_page_config(page_title="Model Performance — NewsVerify", page_icon="📈", layout="wide")

st.title("📈 Machine Learning Performance & Benchmarks")
st.markdown(
    "Empirical evaluation metrics calculated strictly on held-out test and validation sets. "
    "NextGen NewsVerify does not publish synthetic or unverified benchmark scores."
)

repo = AnalysisRepository()
active_version = repo.get_active_model_version()

metadata_file = os.path.join("models", "model_metadata.json")
metadata = {}
if os.path.exists(metadata_file):
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        st.warning(f"Failed to read model metadata: {e}")

if not metadata and not active_version:
    st.warning(
        "⚠️ No trained model pipeline found. Train a model with actual data using:\n\n"
        "```bash\npython -m ml.train --data data/news_sample.csv --text-column text --label-column label\n```"
    )
else:
    model_type = metadata.get("model_type") or active_version.get("model_type", "Unknown")
    version_tag = metadata.get("version_tag") or active_version.get("version_tag", "Unknown")
    trained_at = metadata.get("trained_at", "N/A")
    dataset_name = metadata.get("dataset_source") or active_version.get("dataset_source", "Unknown")

    st.subheader(f"Active Model: {model_type} (`{version_tag}`)")
    st.caption(f"Trained: {trained_at} | Dataset Source: `{dataset_name}`")

    # Top metrics
    test_metrics = metadata.get("test_metrics", {})
    if test_metrics:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Held-Out Test Accuracy", f"{test_metrics.get('accuracy', 0):.2%}")
        m2.metric("Macro F1-Score", f"{test_metrics.get('macro_f1', 0):.4f}")
        m3.metric("Macro Precision", f"{test_metrics.get('macro_precision', 0):.4f}")
        m4.metric("Macro Recall", f"{test_metrics.get('macro_recall', 0):.4f}")

    st.divider()

    # Model comparison table
    st.subheader("Candidate Model Comparison (Validation Split)")
    st.markdown(
        "During the training stage, three candidate architectures are trained with identical pipelines "
        "and compared on the validation set to select the optimal model:"
    )
    val_comp = metadata.get("validation_comparison", {})
    if val_comp:
        rows = []
        for model_name, m_dict in val_comp.items():
            rows.append({
                "Architecture": model_name,
                "Validation Accuracy": f"{m_dict.get('accuracy', 0):.4f}",
                "Macro F1": f"{m_dict.get('macro_f1', 0):.4f}",
                "Macro Precision": f"{m_dict.get('macro_precision', 0):.4f}",
                "Macro Recall": f"{m_dict.get('macro_recall', 0):.4f}",
                "Selected as Active": "✅ Yes" if model_name == model_type else "No",
            })
        df_comp = pd.DataFrame(rows)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

    st.divider()

    # Per-Class & Confusion Matrix
    col_cm, col_pc = st.columns(2)

    with col_cm:
        st.subheader("Held-Out Confusion Matrix")
        cm_data = test_metrics.get("confusion_matrix", {})
        if cm_data and "matrix" in cm_data and "labels" in cm_data:
            matrix = cm_data["matrix"]
            labels = cm_data["labels"]

            fig_cm = px.imshow(
                matrix,
                x=[f"Pred: {lbl}" for lbl in labels],
                y=[f"True: {lbl}" for lbl in labels],
                color_continuous_scale="Blues",
                text_auto=True,
                labels=dict(x="Predicted Class", y="True Class", color="Count"),
            )
            fig_cm.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_cm, use_container_width=True)
        else:
            st.info("Confusion matrix data not available.")

    with col_pc:
        st.subheader("Per-Class Metrics")
        per_class = test_metrics.get("per_class", {})
        if per_class:
            pc_rows = []
            for cls_name, p_metrics in per_class.items():
                pc_rows.append({
                    "Class": cls_name,
                    "Precision": f"{p_metrics.get('precision', 0):.4f}",
                    "Recall": f"{p_metrics.get('recall', 0):.4f}",
                    "F1-Score": f"{p_metrics.get('f1_score', 0):.4f}",
                    "Support": p_metrics.get("support", 0),
                })
            df_pc = pd.DataFrame(pc_rows)
            st.dataframe(df_pc, use_container_width=True, hide_index=True)
        else:
            st.info("Per-class metrics not available.")

    # Calibration Curve if available
    calib = test_metrics.get("calibration")
    if calib and "fraction_of_positives" in calib:
        st.divider()
        st.subheader("Reliability Diagram / Calibration Curve")
        frac_pos = calib["fraction_of_positives"]
        mean_pred = calib["mean_predicted_value"]
        brier = calib.get("brier_score", "N/A")

        st.caption(f"Brier Score Loss: {brier} (Lower is better, evaluates probability calibration)")

        fig_calib = go.Figure()
        fig_calib.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode="lines", line=dict(dash="dash", color="gray"),
            name="Perfect Calibration",
        ))
        fig_calib.add_trace(go.Scatter(
            x=mean_pred, y=frac_pos,
            mode="lines+markers", marker=dict(size=8, color="#3182CE"),
            name="Model Calibration",
        ))
        fig_calib.update_layout(
            xaxis_title="Mean Predicted Probability",
            yaxis_title="Fraction of Positives",
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_calib, use_container_width=True)

    st.divider()
    st.subheader("Retraining Instructions")
    st.code(
        "python -m ml.train --data data/news_sample.csv --text-column text --label-column label --model auto",
        language="bash",
    )
