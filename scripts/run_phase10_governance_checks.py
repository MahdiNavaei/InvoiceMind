from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.audit import verify_audit_chain
from app.services.capacity import estimate_capacity, estimate_cost_per_doc
from app.services.change_management import evaluate_release_gate, runtime_version_snapshot


def main() -> None:
    eval_file = ROOT / "experiments" / "results" / "phase09_evaluation_report.json"
    eval_payload = {}
    if eval_file.exists():
        eval_payload = json.loads(eval_file.read_text(encoding="utf-8"))

    metrics = (eval_payload.get("evaluation") or {}).get("document_metrics") or {}
    baseline = metrics or {
        "doc_pass_rate": 0.9,
        "doc_critical_error_rate": 0.1,
        "critical_false_accept_rate": 0.01,
    }
    release_gate = evaluate_release_gate(metrics=metrics or baseline, baseline=baseline)

    stage_baseline = [
        {"stage": "ingestion", "service_time_ms": 35, "concurrency": 8},
        {"stage": "ocr", "service_time_ms": 480, "concurrency": 2},
        {"stage": "extract", "service_time_ms": 650, "concurrency": 1},
        {"stage": "postprocess", "service_time_ms": 80, "concurrency": 4},
    ]
    capacity = estimate_capacity(stage_baseline, safety_margin=2.0)
    cost = estimate_cost_per_doc(
        infra_cost_per_hour=4.5,
        gpu_seconds_per_doc=3.2,
        cpu_seconds_per_doc=1.4,
        storage_cost_per_doc=0.003,
        review_ratio=0.28,
        review_minutes_per_doc=1.3,
        reviewer_cost_per_hour=15.0,
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_versions": runtime_version_snapshot(),
        "audit_chain": verify_audit_chain(),
        "release_gate": release_gate,
        "capacity": capacity,
        "cost": cost,
        "canary_rollout_plan": {
            "steps": ["1%", "5%", "25%", "100%"],
            "rollback_triggers": [
                "critical_false_accept_guard=false",
                "p95 latency breach sustained",
                "pipeline_exception spike",
            ],
        },
    }

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase10_governance_report.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
