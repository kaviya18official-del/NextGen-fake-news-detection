"""Report generation service for NextGen NewsVerify.

Generates structured JSON exports and publication-grade PDF verification dossiers
using ReportLab. Clearly separates ML predictions from external fact-check evidence.
"""

from __future__ import annotations

import io
import json
import xml.sax.saxutils as saxutils
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class ReportGenerator:
    """Produces verified forensic PDF dossiers and JSON representations."""

    @staticmethod
    def generate_json_report(analysis: Dict[str, Any]) -> str:
        """Export the full analysis dictionary as formatted JSON."""
        return json.dumps(analysis, indent=2, default=str)

    @classmethod
    def generate_pdf_report(cls, analysis: Dict[str, Any]) -> bytes:
        """Generate a structured, professional PDF verification report in memory."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        # Custom paragraph styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1A365D"),
            alignment=0,
        )
        heading2 = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body = ParagraphStyle(
            "BodySmall",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#2D3748"),
        )
        bold_label = ParagraphStyle(
            "BoldLabel",
            parent=body,
            fontName="Helvetica-Bold",
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Italic"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#718096"),
        )

        story = []

        # Header Title
        story.append(Paragraph("NextGen NewsVerify — Forensic Analysis Dossier", title_style))
        story.append(Paragraph(f"Analysis ID: {analysis.get('id', 'N/A')} | Generated: {analysis.get('created_at', 'UTC')}", disclaimer_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3182CE"), spaceBefore=6, spaceAfter=12))

        # 1. Article Overview
        story.append(Paragraph("1. Article Identification & Provenance", heading2))
        art_title = saxutils.escape(analysis.get("article_title") or "Untitled Article")
        art_url = saxutils.escape(analysis.get("article_url") or "Manual / Pasted Input")
        art_pub = saxutils.escape(analysis.get("article_publisher") or "Not Specified")
        art_date = saxutils.escape(analysis.get("publication_date") or "Not Specified")

        overview_data = [
            [Paragraph("Title", bold_label), Paragraph(art_title, body)],
            [Paragraph("Publisher / Domain", bold_label), Paragraph(art_pub, body)],
            [Paragraph("Publication Date", bold_label), Paragraph(art_date, body)],
            [Paragraph("Source URL", bold_label), Paragraph(art_url, body)],
        ]
        t_overview = Table(overview_data, colWidths=[120, 410])
        t_overview.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDF2F7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_overview)
        story.append(Spacer(1, 10))

        # 2. Machine Learning Auxiliary Classification
        story.append(Paragraph("2. Machine Learning Pattern Classification (Auxiliary Signal)", heading2))
        ml_pred = analysis.get("ml_prediction") or "Model Not Executed"
        ml_score = analysis.get("ml_score")
        score_str = f"{ml_score:.4f}" if ml_score is not None else "N/A"
        score_type = analysis.get("ml_score_type") or "N/A"
        ml_ver = analysis.get("model_version") or "N/A"
        uncertainty = analysis.get("ml_uncertainty") or "N/A"

        ml_data = [
            [Paragraph("Classification Prediction", bold_label), Paragraph(str(ml_pred), body)],
            [Paragraph("Model Score / Type", bold_label), Paragraph(f"{score_str} ({score_type})", body)],
            [Paragraph("Statistical Uncertainty", bold_label), Paragraph(str(uncertainty), body)],
            [Paragraph("Model Architecture & Version", bold_label), Paragraph(str(ml_ver), body)],
        ]
        t_ml = Table(ml_data, colWidths=[160, 370])
        t_ml.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_ml)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "Important Caveat: The ML model prediction reflects statistical stylistic and vocabulary "
            "correlations within the training corpus. It does NOT independently verify real-world factual truth.",
            disclaimer_style,
        ))
        story.append(Spacer(1, 10))

        # 3. Investigated Claims & External Fact-Checks
        story.append(Paragraph("3. Extracted Claims & Fact-Check Evidence Status", heading2))
        claims = analysis.get("claims", [])
        if not claims:
            story.append(Paragraph("No individual claims were selected for investigation.", body))
        else:
            for idx, c in enumerate(claims, start=1):
                c_text = saxutils.escape(c.get("original_sentence", ""))
                ass = c.get("evidence_assessment") or {}
                ev_status = ass.get("evidence_status", "lookup_unavailable")
                ev_expl = saxutils.escape(ass.get("status_explanation", "No details available."))

                # Status color banner
                status_bg = colors.HexColor("#E2E8F0")
                if ev_status == "prior_fact_check_found":
                    status_bg = colors.HexColor("#EBF8FF")
                elif ev_status == "evidence_conflict":
                    status_bg = colors.HexColor("#FFF5F5")

                claim_block = [
                    [Paragraph(f"Claim #{idx}: {c_text}", bold_label)],
                    [Paragraph(f"Evidence Status: <b>{ev_status.upper().replace('_', ' ')}</b>", body)],
                    [Paragraph(f"Assessment: {ev_expl}", body)],
                ]

                # List matched reviews if any
                reviews = c.get("fact_checks", [])
                rel_reviews = [r for r in reviews if r.get("match_classification") in ("relevant_match", "related_candidate")]
                if rel_reviews:
                    rev_summary = "<b>Retrieved Fact-Checks:</b><br/>"
                    for r in rel_reviews:
                        pub = saxutils.escape(r.get("publisher_name") or "Unknown Publisher")
                        rat = saxutils.escape(r.get("original_rating") or "Unrated")
                        u = saxutils.escape(r.get("review_url") or "No link")
                        rev_summary += f"• <b>{pub}</b>: Rated <i>'{rat}'</i> ({u})<br/>"
                    claim_block.append([Paragraph(rev_summary, body)])

                t_claim = Table(claim_block, colWidths=[530])
                t_claim.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), status_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t_claim)
                story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))

        # 4. Methodology and Limitations
        story.append(Paragraph("4. Investigative Assistant Methodology & Limitations", heading2))
        methodology_text = (
            "NextGen NewsVerify functions as an investigative decision-support assistant rather than "
            "an automatic truth detector. Predictions and evidence statuses are derived through distinct, "
            "uncoupled methods:<br/>"
            "• <b>ML Text Classifier:</b> Evaluates linguistic syntax and n-grams without access to current facts.<br/>"
            "• <b>Claim Extraction:</b> Deterministic heuristic identification of numbers, dates, and named assertions.<br/>"
            "• <b>Fact-Check Matching:</b> Independent query retrieval via Google Fact Check Tools API with lexical similarity scoring.<br/>"
            "• <b>Evidence Assessment:</b> Strict classification into prior checks, no matches, conflicts, or insufficient evidence without calculating arbitrary truth percentages.<br/>"
            "Never conclude an article is factual merely because an ML classifier predicted it as real, nor that a claim is false simply because no prior fact-check was indexed."
        )
        story.append(Paragraph(methodology_text, body))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
