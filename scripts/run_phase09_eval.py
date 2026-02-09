from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.services.calibration import brier_score, expected_calibration_error, fit_isotonic, fit_platt_scaler, sweep_risk_threshold
from app.services.evaluation_protocol import evaluate_gold_records, load_gold_records
from app.services.labelops import compute_field_level_iaa, detect_benchmark_contamination


def main() -> None:
    benchmark_path = ROOT / "experiments" / "goldset" / "GS-20260209-v1" / "Gold-Benchmark.jsonl"
    dev_path = ROOT / "experiments" / "goldset" / "GS-20260209-v1" / "Gold-Dev.jsonl"
    edge_path = ROOT / "experiments" / "goldset" / "GS-20260209-v1" / "Gold-EdgeCases.jsonl"
    adjudication_path = ROOT / "experiments" / "goldset" / "GS-20260209-v1" / "labelops" / "Adjudication_Log.jsonl"

    benchmark_records = load_gold_records(benchmark_path)
    eval_result = evaluate_gold_records(benchmark_records)

    # Build calibration dataset from benchmark.
    raw_scores = [float(record.get("raw_confidence", 0.5)) for record in benchmark_records]
    correctness_labels = [1 if row["expected_decision"] == "AUTO_APPROVED" else 0 for row in eval_result["records"]]
    critical_error_labels = [1 if row["expected_decision"] == "NEEDS_REVIEW" else 0 for row in eval_result["records"]]

    isotonic = fit_isotonic(raw_scores, correctness_labels)
    platt = fit_platt_scaler(raw_scores, correctness_labels)
    isotonic_probs = [isotonic.predict(score) for score in raw_scores]
    platt_probs = [platt.predict(score) for score in raw_scores]

    calibration_report = {
        "raw": {
            "ece": expected_calibration_error(raw_scores, correctness_labels),
            "brier": brier_score(raw_scores, correctness_labels),
        },
        "isotonic": {
            "ece": expected_calibration_error(isotonic_probs, correctness_labels),
            "brier": brier_score(isotonic_probs, correctness_labels),
            "breakpoints": list(zip(isotonic.thresholds, isotonic.values, strict=False)),
        },
        "platt": {
            "ece": expected_calibration_error(platt_probs, correctness_labels),
            "brier": brier_score(platt_probs, correctness_labels),
            "params": {"a": platt.a, "b": platt.b},
        },
    }

    risks = [1.0 - prob for prob in isotonic_probs]
    threshold_pick = sweep_risk_threshold(
        risks=risks,
        critical_error_labels=critical_error_labels,
        critical_false_accept_ceiling=settings.critical_false_accept_ceiling,
    )

    adjudication_rows = load_gold_records(adjudication_path)
    iaa = compute_field_level_iaa(adjudication_rows)

    contamination = detect_benchmark_contamination(
        benchmark_doc_ids=[record.get("doc_id") for record in benchmark_records],
        tuning_doc_ids=[record.get("doc_id") for record in load_gold_records(dev_path)] + [record.get("doc_id") for record in load_gold_records(edge_path)],
    )

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "goldset_version": "GS-20260209-v1",
        "evaluation": eval_result,
        "calibration": calibration_report,
        "threshold_selection": threshold_pick,
        "labelops": {
            "iaa": iaa,
            "benchmark_contamination": contamination,
        },
    }

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase09_evaluation_report.json"
    out_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
