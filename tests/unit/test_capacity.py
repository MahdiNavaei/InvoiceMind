from app.services.capacity import estimate_capacity, estimate_cost_per_doc


def test_capacity_estimation():
    result = estimate_capacity(
        [
            {"stage": "ocr", "service_time_ms": 500, "concurrency": 2},
            {"stage": "extract", "service_time_ms": 800, "concurrency": 1},
        ],
        safety_margin=2.0,
    )
    assert result["capacity_system_docs_per_sec"] > 0
    assert result["recommended_peak_lambda"] > 0


def test_cost_per_doc_estimation():
    result = estimate_cost_per_doc(
        infra_cost_per_hour=5.0,
        gpu_seconds_per_doc=4.0,
        cpu_seconds_per_doc=2.0,
        storage_cost_per_doc=0.003,
        review_ratio=0.25,
        review_minutes_per_doc=1.2,
        reviewer_cost_per_hour=15.0,
    )
    assert result["cost_per_doc"] > 0
    assert result["review_cost_per_doc"] > 0
