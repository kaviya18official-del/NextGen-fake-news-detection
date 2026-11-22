"""Database package for NextGen NewsVerify.

Provides SQLite models, connection factory, and repository operations.
"""

from database.connection import get_db, init_db, DB_PATH
from database.models import (
    Analysis,
    Claim,
    FactCheckReview,
    EvidenceAssessment,
    ModelVersion,
    AnalysisFeedback,
)
from database.repository import AnalysisRepository

__all__ = [
    "get_db",
    "init_db",
    "DB_PATH",
    "Analysis",
    "Claim",
    "FactCheckReview",
    "EvidenceAssessment",
    "ModelVersion",
    "AnalysisFeedback",
    "AnalysisRepository",
]
