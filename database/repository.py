"""Repository layer for database operations in NextGen NewsVerify.

Provides structured, safe methods to save, query, paginate, and delete analyses,
claims, reviews, evidence assessments, and model metadata.
"""

from __future__ import annotations

import datetime
import json
from typing import Optional, List, Dict, Any

from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload, Session

from database.connection import get_db, init_db
from database.models import (
    Analysis,
    Claim,
    FactCheckReview,
    EvidenceAssessment,
    ModelVersion,
    AnalysisFeedback,
)


class AnalysisRepository:
    """Repository handling all database interactions with transaction safety."""

    def __init__(self):
        init_db()

    def save_analysis(
        self,
        analysis_dict: Dict[str, Any],
        claims_data: List[Dict[str, Any]],
        assessments_data: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Persist a complete analysis record including claims, reviews, and assessments."""
        with get_db() as db:
            analysis = Analysis(
                id=analysis_dict["id"],
                input_type=analysis_dict.get("input_type", "text"),
                article_title=analysis_dict.get("article_title"),
                article_url=analysis_dict.get("article_url"),
                article_publisher=analysis_dict.get("article_publisher"),
                publication_date=analysis_dict.get("publication_date"),
                article_preview=analysis_dict.get("article_preview"),
                article_text_hash=analysis_dict.get("article_text_hash", ""),
                model_version=analysis_dict.get("model_version"),
                ml_prediction=analysis_dict.get("ml_prediction"),
                ml_score=analysis_dict.get("ml_score"),
                ml_score_type=analysis_dict.get("ml_score_type"),
                ml_uncertainty=analysis_dict.get("ml_uncertainty"),
                ml_explanation_json=json.dumps(analysis_dict.get("ml_explanation"))
                if analysis_dict.get("ml_explanation")
                else None,
                overall_evidence_summary=analysis_dict.get("overall_evidence_summary"),
                processing_time_ms=analysis_dict.get("processing_time_ms", 0.0),
                status=analysis_dict.get("status", "completed"),
                error_message=analysis_dict.get("error_message"),
            )
            db.add(analysis)
            db.flush()  # populate ID

            # Add claims and their fact-checks
            claim_obj_map: Dict[int, Claim] = {}
            for c_idx, c_dict in enumerate(claims_data):
                claim_obj = Claim(
                    analysis_id=analysis.id,
                    claim_index=c_dict.get("claim_index", c_idx),
                    original_sentence=c_dict["original_sentence"],
                    normalized_query=c_dict.get("normalized_query", c_dict["original_sentence"]),
                    claim_type=c_dict.get("claim_type", "factual_assertion"),
                    is_selected=c_dict.get("is_selected", True),
                )
                db.add(claim_obj)
                db.flush()
                claim_obj_map[claim_obj.claim_index] = claim_obj

                # Add associated reviews
                for rev in c_dict.get("fact_checks", []):
                    review_obj = FactCheckReview(
                        claim_id=claim_obj.id,
                        query_used=rev.get("query_used", claim_obj.normalized_query),
                        query_status=rev.get("query_status", "no_match"),
                        claim_text_from_review=rev.get("claim_text_from_review"),
                        publisher_name=rev.get("publisher_name"),
                        publisher_site=rev.get("publisher_site"),
                        original_rating=rev.get("original_rating"),
                        review_url=rev.get("review_url"),
                        review_date=rev.get("review_date"),
                        lexical_similarity_score=rev.get("lexical_similarity_score"),
                        match_classification=rev.get("match_classification"),
                    )
                    db.add(review_obj)

            # Add assessments if provided
            if assessments_data:
                for ass in assessments_data:
                    c_idx = ass.get("claim_index", 0)
                    claim_obj = claim_obj_map.get(c_idx)
                    if claim_obj:
                        assessment_obj = EvidenceAssessment(
                            analysis_id=analysis.id,
                            claim_id=claim_obj.id,
                            evidence_status=ass["evidence_status"],
                            status_explanation=ass.get("status_explanation", ""),
                            conflicting_reviews_json=json.dumps(ass.get("conflicting_reviews"))
                            if ass.get("conflicting_reviews")
                            else None,
                            limitations=ass.get("limitations"),
                        )
                        db.add(assessment_obj)

            return analysis.id

    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of an analysis by ID."""
        with get_db() as db:
            analysis = (
                db.query(Analysis)
                .options(
                    joinedload(Analysis.claims).joinedload(Claim.fact_checks),
                    joinedload(Analysis.claims).joinedload(Claim.evidence_assessment),
                )
                .filter(Analysis.id == analysis_id)
                .first()
            )
            if not analysis:
                return None

            return self._serialize_analysis(analysis)

    def list_analyses(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List analyses with optional filtering and pagination."""
        with get_db() as db:
            q = db.query(Analysis)
            if status_filter:
                q = q.filter(Analysis.status == status_filter)
            if search_query:
                pattern = f"%{search_query.strip()}%"
                q = q.filter(
                    (Analysis.article_title.ilike(pattern))
                    | (Analysis.article_url.ilike(pattern))
                    | (Analysis.article_preview.ilike(pattern))
                )

            analyses = (
                q.order_by(desc(Analysis.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": a.id,
                    "input_type": a.input_type,
                    "article_title": a.article_title or "Untitled",
                    "article_url": a.article_url,
                    "article_publisher": a.article_publisher,
                    "ml_prediction": a.ml_prediction,
                    "ml_score": a.ml_score,
                    "ml_score_type": a.ml_score_type,
                    "model_version": a.model_version,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "preview": a.article_preview[:150] if a.article_preview else "",
                }
                for a in analyses
            ]

    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete an analysis and cascade to all claims, reviews, and assessments."""
        with get_db() as db:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if not analysis:
                return False
            db.delete(analysis)
            return True

    def delete_older_than(self, days: int) -> int:
        """Purge records older than specified retention days."""
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        with get_db() as db:
            old_records = db.query(Analysis).filter(Analysis.created_at < cutoff).all()
            count = len(old_records)
            for rec in old_records:
                db.delete(rec)
            return count

    def get_statistics(self) -> Dict[str, Any]:
        """Compute aggregate usage statistics."""
        with get_db() as db:
            total_analyses = db.query(func.count(Analysis.id)).scalar() or 0
            total_claims = db.query(func.count(Claim.id)).scalar() or 0
            total_reviews = db.query(func.count(FactCheckReview.id)).scalar() or 0

            # Evidence status breakdown
            status_counts = (
                db.query(EvidenceAssessment.evidence_status, func.count(EvidenceAssessment.id))
                .group_by(EvidenceAssessment.evidence_status)
                .all()
            )
            status_map = {st: cnt for st, cnt in status_counts}

            # ML prediction breakdown
            pred_counts = (
                db.query(Analysis.ml_prediction, func.count(Analysis.id))
                .filter(Analysis.ml_prediction.isnot(None))
                .group_by(Analysis.ml_prediction)
                .all()
            )
            pred_map = {pr: cnt for pr, cnt in pred_counts}

            return {
                "total_analyses": total_analyses,
                "total_claims": total_claims,
                "total_reviews": total_reviews,
                "evidence_status_breakdown": status_map,
                "ml_prediction_breakdown": pred_map,
            }

    def record_feedback(self, analysis_id: str, feedback_type: str, comment: Optional[str] = None) -> bool:
        """Save user feedback on a verification outcome."""
        with get_db() as db:
            feedback = AnalysisFeedback(
                analysis_id=analysis_id,
                feedback_type=feedback_type,
                comment=comment,
            )
            db.add(feedback)
            return True

    def save_model_version(self, model_info: Dict[str, Any]) -> int:
        """Record a trained model version and mark it active."""
        with get_db() as db:
            # Optionally deactivate previous active versions if this is marked active
            if model_info.get("is_active", True):
                db.query(ModelVersion).update({ModelVersion.is_active: False})

            mv = ModelVersion(
                version_tag=model_info["version_tag"],
                model_type=model_info["model_type"],
                dataset_source=model_info.get("dataset_source", "unknown"),
                num_samples=model_info.get("num_samples", 0),
                accuracy=model_info.get("accuracy"),
                precision=model_info.get("precision"),
                recall=model_info.get("recall"),
                f1_score=model_info.get("f1_score"),
                is_active=model_info.get("is_active", True),
                metadata_json=json.dumps(model_info.get("metadata", {})),
            )
            db.add(mv)
            db.flush()
            return mv.id

    def get_active_model_version(self) -> Optional[Dict[str, Any]]:
        """Get the currently active model record."""
        with get_db() as db:
            mv = (
                db.query(ModelVersion)
                .filter(ModelVersion.is_active.is_(True))
                .order_by(desc(ModelVersion.created_at))
                .first()
            )
            if not mv:
                # Fallback to the latest trained model
                mv = db.query(ModelVersion).order_by(desc(ModelVersion.created_at)).first()
            if not mv:
                return None
            return {
                "version_tag": mv.version_tag,
                "model_type": mv.model_type,
                "dataset_source": mv.dataset_source,
                "num_samples": mv.num_samples,
                "accuracy": mv.accuracy,
                "precision": mv.precision,
                "recall": mv.recall,
                "f1_score": mv.f1_score,
                "metadata": json.loads(mv.metadata_json) if mv.metadata_json else {},
                "created_at": mv.created_at.isoformat() if mv.created_at else None,
            }

    def list_model_versions(self) -> List[Dict[str, Any]]:
        """List all recorded model versions."""
        with get_db() as db:
            mvs = db.query(ModelVersion).order_by(desc(ModelVersion.created_at)).all()
            return [
                {
                    "id": m.id,
                    "version_tag": m.version_tag,
                    "model_type": m.model_type,
                    "dataset_source": m.dataset_source,
                    "num_samples": m.num_samples,
                    "accuracy": m.accuracy,
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1_score": m.f1_score,
                    "is_active": m.is_active,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "metadata": json.loads(m.metadata_json) if m.metadata_json else {},
                }
                for m in mvs
            ]

    def _serialize_analysis(self, analysis: Analysis) -> Dict[str, Any]:
        """Convert SQLAlchemy Analysis object and relationships into a clean dictionary."""
        claims_list = []
        for c in analysis.claims:
            reviews_list = [
                {
                    "query_used": r.query_used,
                    "query_status": r.query_status,
                    "claim_text_from_review": r.claim_text_from_review,
                    "publisher_name": r.publisher_name,
                    "publisher_site": r.publisher_site,
                    "original_rating": r.original_rating,
                    "review_url": r.review_url,
                    "review_date": r.review_date,
                    "lexical_similarity_score": r.lexical_similarity_score,
                    "match_classification": r.match_classification,
                }
                for r in c.fact_checks
            ]

            assessment_dict = None
            if c.evidence_assessment:
                assessment_dict = {
                    "evidence_status": c.evidence_assessment.evidence_status,
                    "status_explanation": c.evidence_assessment.status_explanation,
                    "conflicting_reviews": json.loads(c.evidence_assessment.conflicting_reviews_json)
                    if c.evidence_assessment.conflicting_reviews_json
                    else [],
                    "limitations": c.evidence_assessment.limitations,
                }

            claims_list.append(
                {
                    "id": c.id,
                    "claim_index": c.claim_index,
                    "original_sentence": c.original_sentence,
                    "normalized_query": c.normalized_query,
                    "claim_type": c.claim_type,
                    "is_selected": c.is_selected,
                    "fact_checks": reviews_list,
                    "evidence_assessment": assessment_dict,
                }
            )

        return {
            "id": analysis.id,
            "input_type": analysis.input_type,
            "article_title": analysis.article_title,
            "article_url": analysis.article_url,
            "article_publisher": analysis.article_publisher,
            "publication_date": analysis.publication_date,
            "article_preview": analysis.article_preview,
            "article_text_hash": analysis.article_text_hash,
            "model_version": analysis.model_version,
            "ml_prediction": analysis.ml_prediction,
            "ml_score": analysis.ml_score,
            "ml_score_type": analysis.ml_score_type,
            "ml_uncertainty": analysis.ml_uncertainty,
            "ml_explanation": json.loads(analysis.ml_explanation_json)
            if analysis.ml_explanation_json
            else None,
            "overall_evidence_summary": analysis.overall_evidence_summary,
            "processing_time_ms": analysis.processing_time_ms,
            "status": analysis.status,
            "error_message": analysis.error_message,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "claims": claims_list,
        }
