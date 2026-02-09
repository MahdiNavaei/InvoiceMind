from app.services.review_policy import evaluate_review_decision


def _good_result() -> dict:
    return {
        "invoice_no": "INV-100",
        "invoice_date": "2026-02-09",
        "vendor_name": "Sample Vendor",
        "currency": "USD",
        "subtotal": 100.0,
        "tax": 8.0,
        "total": 108.0,
        "field_evidence": {
            "invoice_no": [{"page": 1, "snippet": "INV-100"}],
            "invoice_date": [{"page": 1, "snippet": "2026-02-09"}],
            "vendor_name": [{"page": 1, "snippet": "Sample Vendor"}],
            "currency": [{"page": 1, "snippet": "USD"}],
            "total": [{"page": 1, "snippet": "108.0"}],
        },
    }


def test_review_policy_auto_approved_when_all_gates_pass():
    decision = evaluate_review_decision(
        result=_good_result(),
        issues=[],
        extraction_confidence=0.95,
        ocr_confidence=0.93,
        quality_tier="HIGH",
        quality_score=0.91,
    )
    assert decision["decision"] == "AUTO_APPROVED"
    assert decision["reason_codes"] == []


def test_review_policy_required_field_missing():
    result = _good_result()
    result["invoice_no"] = ""
    decision = evaluate_review_decision(
        result=result,
        issues=[],
        extraction_confidence=0.95,
        ocr_confidence=0.93,
        quality_tier="HIGH",
        quality_score=0.91,
    )
    assert decision["decision"] == "NEEDS_REVIEW"
    assert "REQ_FIELD_MISSING" in decision["reason_codes"]


def test_review_policy_low_quality_escalation():
    decision = evaluate_review_decision(
        result=_good_result(),
        issues=[],
        extraction_confidence=0.45,
        ocr_confidence=0.40,
        quality_tier="LOW",
        quality_score=0.32,
    )
    assert decision["decision"] == "NEEDS_REVIEW"
    assert "LOW_QUALITY_INPUT" in decision["reason_codes"]
