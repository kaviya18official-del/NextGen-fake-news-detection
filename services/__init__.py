"""Services package for NextGen NewsVerify.

Provides article extraction, claim extraction, fact-check lookups,
evidence matching, source analysis, OCR, and report generation.
"""

from services.article_extractor import ArticleExtractor
from services.claim_extractor import ClaimExtractor
from services.fact_check_service import FactCheckService
from services.claim_matcher import ClaimMatcher
from services.evidence_assessor import EvidenceAssessor
from services.source_analyzer import SourceAnalyzer
from services.ocr_service import OCRService
from services.report_generator import ReportGenerator

__all__ = [
    "ArticleExtractor",
    "ClaimExtractor",
    "FactCheckService",
    "ClaimMatcher",
    "EvidenceAssessor",
    "SourceAnalyzer",
    "OCRService",
    "ReportGenerator",
]
