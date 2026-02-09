from __future__ import annotations

from typing import Any


def estimate_capacity(stages: list[dict[str, Any]], *, safety_margin: float = 2.0) -> dict[str, Any]:
    if not stages:
        return {"capacity_system_docs_per_sec": 0.0, "stage_capacities": [], "recommended_peak_lambda": 0.0}

    stage_caps = []
    for stage in stages:
        service_ms = max(1e-6, float(stage.get("service_time_ms", 1.0)))
        concurrency = max(1e-6, float(stage.get("concurrency", 1.0)))
        capacity = concurrency / (service_ms / 1000.0)
        stage_caps.append(
            {
                "stage": stage.get("stage", "unknown"),
                "service_time_ms": service_ms,
                "concurrency": concurrency,
                "capacity_docs_per_sec": capacity,
            }
        )
    system_capacity = min(item["capacity_docs_per_sec"] for item in stage_caps)
    return {
        "capacity_system_docs_per_sec": system_capacity,
        "recommended_peak_lambda": system_capacity / max(1.0, safety_margin),
        "stage_capacities": stage_caps,
    }


def estimate_cost_per_doc(
    *,
    infra_cost_per_hour: float,
    gpu_seconds_per_doc: float,
    cpu_seconds_per_doc: float,
    storage_cost_per_doc: float,
    review_ratio: float,
    review_minutes_per_doc: float,
    reviewer_cost_per_hour: float,
) -> dict[str, float]:
    infra_per_second = infra_cost_per_hour / 3600.0
    infra_cost_doc = infra_per_second * (gpu_seconds_per_doc + cpu_seconds_per_doc)
    review_cost_doc = (review_minutes_per_doc / 60.0) * reviewer_cost_per_hour * max(0.0, min(1.0, review_ratio))
    total = infra_cost_doc + storage_cost_per_doc + review_cost_doc
    return {
        "infra_cost_per_doc": infra_cost_doc,
        "storage_cost_per_doc": storage_cost_per_doc,
        "review_cost_per_doc": review_cost_doc,
        "cost_per_doc": total,
    }
