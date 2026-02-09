from app.services.evaluation_protocol import evaluate_gold_records


def test_evaluation_protocol_computes_document_metrics():
    records = [
        {
            "doc_id": "d1",
            "quality_tier": "HIGH",
            "decision": "AUTO_APPROVED",
            "ground_truth": {
                "invoice_no": "INV-1",
                "invoice_date": "2026-02-01",
                "vendor_name": "A",
                "currency": "USD",
                "subtotal": 100.0,
                "tax": 8.0,
                "total": 108.0,
            },
            "prediction": {
                "invoice_no": "INV-1",
                "invoice_date": "2026-02-01",
                "vendor_name": "A",
                "currency": "USD",
                "subtotal": 100.0,
                "tax": 8.0,
                "total": 108.0,
                "field_evidence": {
                    "invoice_no": [{"page": 1}],
                    "invoice_date": [{"page": 1}],
                    "vendor_name": [{"page": 1}],
                    "total": [{"page": 1}],
                },
            },
        },
        {
            "doc_id": "d2",
            "quality_tier": "LOW",
            "decision": "NEEDS_REVIEW",
            "ground_truth": {
                "invoice_no": "INV-2",
                "invoice_date": "2026-02-02",
                "vendor_name": "B",
                "currency": "USD",
                "subtotal": 100.0,
                "tax": 8.0,
                "total": 108.0,
            },
            "prediction": {
                "invoice_no": "",
                "invoice_date": "2026-02-02",
                "vendor_name": "B",
                "currency": "USD",
                "subtotal": 100.0,
                "tax": 8.0,
                "total": 108.0,
                "field_evidence": {"vendor_name": [{"page": 1}]},
            },
        },
    ]
    result = evaluate_gold_records(records)
    result2 = evaluate_gold_records(records)
    assert result["dataset_size"] == 2
    assert result["document_metrics"] == result2["document_metrics"]
    assert "invoice_number" in result["field_metrics"]
    assert result["document_metrics"]["review_ratio"] >= 0.5
