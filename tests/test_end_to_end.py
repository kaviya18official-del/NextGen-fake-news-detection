"""End-to-End integration test covering all 10 pipeline steps of NextGen NewsVerify."""

import uuid
from unittest.mock import patch, MagicMock

from security.input_validator import validate_text_input
from services.article_extractor import ArticleExtractor
from ml.predict import NewsClassifierPredictor
from services.claim_extractor import ClaimExtractor
from services.fact_check_service import FactCheckService
from services.claim_matcher import ClaimMatcher
from services.evidence_assessor import EvidenceAssessor
from database.repository import AnalysisRepository
from services.report_generator import ReportGenerator


def test_full_news_verification_pipeline_e2e():
    """Execute complete 10-step analysis pipeline from raw text to database and PDF report."""
    raw_article_text = (
        "The World Health Organization confirmed an increase in seasonal influenza cases across parts "
        "of the Northern Hemisphere on Monday. Public health officials reported that hospital admissions "
        "rose 12 percent compared to the same period last year. Medical researchers advised vulnerable "
        "populations to receive annual vaccinations before the winter peak. Meanwhile, unverified claims "
        "circulated online alleging that vaccines contain synthetic bioluminescent nanobots emitting radio signals."
    )

    # Step 1: Accept & validate input
    is_valid, err_msg, cleaned_text = validate_text_input(raw_article_text)
    assert is_valid is True
    assert err_msg == ""
    analysis_id = str(uuid.uuid4())

    # Step 2: Normalize article text
    normalized_text = ArticleExtractor.normalize_pasted_text(cleaned_text)
    assert len(normalized_text) > 50

    # Step 3: Run ML classifier
    predictor = NewsClassifierPredictor()
    ml_result = predictor.predict(normalized_text)
    assert ml_result["prediction"] in ("Real", "Fake")
    assert ml_result["score"] is not None

    # Step 4: Extract checkable claims
    claim_extractor = ClaimExtractor(max_claims=3)
    claims = claim_extractor.extract_claims(normalized_text)
    assert len(claims) >= 1

    # Step 5 & 6: Fact-check search & matching (Mocked API)
    fact_service = FactCheckService(api_key="TEST_API_KEY")
    matcher = ClaimMatcher()
    assessor = EvidenceAssessor()

    mock_fact_check_response = {
        "claims": [
            {
                "text": "Vaccines contain synthetic bioluminescent nanobots that emit signals.",
                "claimReview": [
                    {
                        "publisher": {"name": "Health Feedback"},
                        "url": "https://healthfeedback.org/claimreview/nanobots-claim",
                        "textualRating": "Inaccurate / False",
                        "reviewDate": "2024-03-01",
                    }
                ],
            }
        ]
    }

    analyzed_claims_data = []
    assessments_data = []

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_fact_check_response
        mock_get.return_value = mock_resp

        for c in claims:
            # Step 5: Search
            search_res = fact_service.search_claim(c["normalized_query"])
            # Step 6: Match
            matched_reviews = matcher.match_reviews_to_claim(
                c["original_sentence"], search_res.get("reviews", [])
            )
            c["fact_checks"] = matched_reviews

            # Step 7: Assess evidence status
            assessment = assessor.assess_claim_evidence(
                search_res.get("query_status", "no_match"), matched_reviews
            )
            assessment["claim_index"] = c["claim_index"]
            assessments_data.append(assessment)
            analyzed_claims_data.append(c)

    # Step 8: Combine results (Without inventing a truth score!)
    analysis_record = {
        "id": analysis_id,
        "input_type": "text",
        "article_title": "World Health Organization Influenza Advisory",
        "article_preview": normalized_text[:300],
        "article_text_hash": "e2e_test_hash",
        "model_version": ml_result["model_version"],
        "ml_prediction": ml_result["prediction"],
        "ml_score": ml_result["score"],
        "ml_score_type": ml_result["score_type"],
        "ml_uncertainty": ml_result["uncertainty"],
        "ml_explanation": ml_result["explanation"],
        "status": "completed",
    }

    # Step 9: Save to Database
    repo = AnalysisRepository()
    saved_id = repo.save_analysis(analysis_record, analyzed_claims_data, assessments_data)
    assert saved_id == analysis_id

    # Retrieve from DB to confirm full persistence
    persisted_dossier = repo.get_analysis(saved_id)
    assert persisted_dossier is not None
    assert len(persisted_dossier["claims"]) == len(analyzed_claims_data)

    # Step 10: Generate Reports
    json_report = ReportGenerator.generate_json_report(persisted_dossier)
    assert '"id":' in json_report

    pdf_report = ReportGenerator.generate_pdf_report(persisted_dossier)
    assert isinstance(pdf_report, bytes)
    assert pdf_report.startswith(b"%PDF-")
