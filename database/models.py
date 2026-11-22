"""SQLAlchemy data models for NextGen NewsVerify.

Includes tables for analyses, claims, fact-check reviews, evidence assessments,
model versions, and user feedback.
"""

from __future__ import annotations

import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from database.connection import Base


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class ModelVersion(Base):
    """Tracks trained ML model versions, architectures, and evaluation metrics."""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_tag = Column(String(64), unique=True, nullable=False, index=True)
    model_type = Column(String(64), nullable=False)  # e.g., LogisticRegression, LinearSVC, MultinomialNB
    dataset_source = Column(String(255), nullable=False)
    num_samples = Column(Integer, default=0)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    metadata_json = Column(Text, nullable=True)


class Analysis(Base):
    """Stores a complete news analysis record."""
    __tablename__ = "analyses"

    id = Column(String(64), primary_key=True, index=True)  # UUID4
    input_type = Column(String(32), nullable=False)  # text, url, image
    article_title = Column(String(512), nullable=True)
    article_url = Column(String(2048), nullable=True)
    article_publisher = Column(String(256), nullable=True)
    publication_date = Column(String(128), nullable=True)
    article_preview = Column(Text, nullable=True)  # privacy-preserving preview
    article_text_hash = Column(String(64), nullable=False, index=True)

    # ML Results
    model_version = Column(String(64), nullable=True)
    ml_prediction = Column(String(64), nullable=True)  # e.g., Real, Fake
    ml_score = Column(Float, nullable=True)
    ml_score_type = Column(String(64), nullable=True)  # calibrated_probability, decision_score
    ml_uncertainty = Column(String(128), nullable=True)
    ml_explanation_json = Column(Text, nullable=True)

    overall_evidence_summary = Column(Text, nullable=True)
    processing_time_ms = Column(Float, default=0.0)
    status = Column(String(32), default="completed", nullable=False)  # completed, partial, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationships with cascade delete
    claims = relationship(
        "Claim",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="Claim.claim_index",
    )
    evidence_assessments = relationship(
        "EvidenceAssessment",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    feedbacks = relationship(
        "AnalysisFeedback",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )


class Claim(Base):
    """Checkable factual claims extracted from an article."""
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_index = Column(Integer, nullable=False)
    original_sentence = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=False)
    claim_type = Column(String(64), default="factual_assertion")  # statistical, quotation, event, etc.
    is_selected = Column(Boolean, default=True)

    analysis = relationship("Analysis", back_populates="claims")
    fact_checks = relationship(
        "FactCheckReview",
        back_populates="claim",
        cascade="all, delete-orphan",
    )
    evidence_assessment = relationship(
        "EvidenceAssessment",
        back_populates="claim",
        uselist=False,
        cascade="all, delete-orphan",
    )


class FactCheckReview(Base):
    """External fact-check reviews retrieved for a claim."""
    __tablename__ = "fact_check_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(
        Integer,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_used = Column(Text, nullable=False)
    query_status = Column(String(32), nullable=False)  # found, no_match, unavailable, not_configured
    claim_text_from_review = Column(Text, nullable=True)
    publisher_name = Column(String(256), nullable=True)
    publisher_site = Column(String(256), nullable=True)
    original_rating = Column(String(128), nullable=True)  # Publisher verdict
    review_url = Column(String(2048), nullable=True)
    review_date = Column(String(128), nullable=True)
    lexical_similarity_score = Column(Float, nullable=True)
    match_classification = Column(String(64), nullable=True)  # relevant_match, related_candidate, rejected_irrelevant
    created_at = Column(DateTime, default=utc_now, nullable=False)

    claim = relationship("Claim", back_populates="fact_checks")


class EvidenceAssessment(Base):
    """Deterministic evidence assessment for a specific claim based on retrieved reviews."""
    __tablename__ = "evidence_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id = Column(
        Integer,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    evidence_status = Column(
        String(64),
        nullable=False,
    )  # prior_fact_check_found, no_matching_fact_check, insufficient_evidence, evidence_conflict, lookup_unavailable
    status_explanation = Column(Text, nullable=False)
    conflicting_reviews_json = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)

    analysis = relationship("Analysis", back_populates="evidence_assessments")
    claim = relationship("Claim", back_populates="evidence_assessment")


class AnalysisFeedback(Base):
    """User feedback on verification results."""
    __tablename__ = "analysis_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(
        String(64),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feedback_type = Column(String(32), nullable=False)  # helpful, unhelpful, flag_error
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    analysis = relationship("Analysis", back_populates="feedbacks")


# Indexes for frequent lookup patterns
Index("idx_analyses_created_at_desc", Analysis.created_at.desc())
Index("idx_fact_check_claim_status", FactCheckReview.claim_id, FactCheckReview.query_status)
