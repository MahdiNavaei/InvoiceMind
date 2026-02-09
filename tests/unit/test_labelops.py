from app.services.labelops import compute_field_level_iaa, detect_benchmark_contamination


def test_compute_iaa():
    rows = [
        {"field": "invoice_no", "annotator_a": "INV-1", "annotator_b": "INV-1"},
        {"field": "invoice_no", "annotator_a": "INV-2", "annotator_b": "INV-22"},
        {"field": "total", "annotator_a": "100", "annotator_b": "100"},
    ]
    result = compute_field_level_iaa(rows)
    assert result["sample_size"] == 3
    assert 0.0 <= result["overall_agreement"] <= 1.0


def test_detect_contamination():
    result = detect_benchmark_contamination(
        benchmark_doc_ids=["a", "b", "c"],
        tuning_doc_ids=["x", "b", "y"],
    )
    assert result["contaminated"] is True
    assert result["overlap_count"] == 1
