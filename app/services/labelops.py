from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_field_level_iaa(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute agreement from adjudication rows.

    Expected row fields:
    - field
    - annotator_a
    - annotator_b
    """
    per_field = defaultdict(lambda: {"agree": 0, "total": 0})
    total_agree = 0
    total = 0
    for row in rows:
        field = str(row.get("field") or "unknown")
        a = _normalize(row.get("annotator_a"))
        b = _normalize(row.get("annotator_b"))
        agree = int(a == b)
        per_field[field]["agree"] += agree
        per_field[field]["total"] += 1
        total_agree += agree
        total += 1

    field_scores = {}
    for field, stats in per_field.items():
        denom = stats["total"] or 1
        field_scores[field] = round(stats["agree"] / denom, 6)

    return {
        "overall_agreement": round((total_agree / total) if total else 0.0, 6),
        "field_agreement": field_scores,
        "sample_size": total,
    }


def detect_benchmark_contamination(
    *,
    benchmark_doc_ids: list[str],
    tuning_doc_ids: list[str],
) -> dict[str, Any]:
    benchmark = set(benchmark_doc_ids)
    tuning = set(tuning_doc_ids)
    overlap = sorted(benchmark.intersection(tuning))
    return {
        "contaminated": len(overlap) > 0,
        "overlap_count": len(overlap),
        "overlap_doc_ids": overlap,
    }


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()
