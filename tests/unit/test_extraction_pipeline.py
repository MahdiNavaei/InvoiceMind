from app.services.extraction import (
    decide_final_status,
    required_field_coverage,
    run_ocr,
    run_structured_extraction,
    validate_result,
)


def test_run_ocr_fallback_and_extract_invoice_schema():
    ocr = run_ocr("non_existing_invoice.png")
    assert ocr.provider in {"deterministic_fallback", "plain_text_reader", "tesseract"}
    assert ocr.text

    extracted = run_structured_extraction(
        text=ocr.text,
        filename="sample_invoice_fa.png",
        language="fa",
        file_path=None,
        ocr_confidence=ocr.confidence,
    )
    assert extracted.result["schema_version"] == "invoice_v1"
    assert extracted.result["currency"] == "IRR"
    assert extracted.result["vendor_name"]
    assert extracted.result["invoice_no"]


def test_validate_and_quality_gate_flags_needs_review_on_low_confidence():
    result = {
        "schema_version": "invoice_v1",
        "vendor_name": "",
        "invoice_no": "",
        "invoice_date": "",
        "subtotal": 100,
        "tax": 9,
        "total": 109,
        "currency": "",
        "evidence": [],
    }
    issues = validate_result(result, extraction_confidence=0.3, ocr_confidence=0.2)
    status, reasons = decide_final_status(
        result,
        issues,
        extraction_confidence=0.3,
        ocr_confidence=0.2,
    )
    assert any(issue["code"] == "MISSING_REQUIRED_FIELDS" for issue in issues)
    assert status == "NEEDS_REVIEW"
    assert "LOW_OCR_CONFIDENCE" in reasons


def test_total_mismatch_is_warning_and_maps_to_warn_status():
    result = {
        "schema_version": "invoice_v1",
        "vendor_name": "Sample Vendor",
        "invoice_no": "INV-100",
        "invoice_date": "2026-02-09",
        "subtotal": 100,
        "tax": 8,
        "total": 150,
        "currency": "USD",
        "evidence": [],
    }
    assert required_field_coverage(result) == 1.0
    issues = validate_result(result, extraction_confidence=0.9, ocr_confidence=0.9)
    status, reasons = decide_final_status(
        result,
        issues,
        extraction_confidence=0.9,
        ocr_confidence=0.9,
    )
    assert any(issue["code"] == "TOTAL_MISMATCH" for issue in issues)
    assert status == "WARN"
    assert reasons == ["NON_CRITICAL_VALIDATION_ISSUES"]
