from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.review_policy import FIELD_NAME_MAP, load_metrics_definitions


@dataclass
class FieldEvaluation:
    name: str
    canonical_key: str
    required: bool
    critical: bool
    weight: float
    evidence_required: bool
    correct: bool
    predicted_present: bool
    gt_present: bool
    evidence_ok: bool


def evaluate_gold_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    metrics_def = load_metrics_definitions()
    field_defs = metrics_def.get("fields", [])
    evidence_threshold = float(metrics_def.get("document_level", {}).get("evidence_coverage_threshold", 0.9))

    total_docs = len(records)
    if total_docs == 0:
        return {
            "dataset_size": 0,
            "field_metrics": {},
            "document_metrics": {},
            "confusion_matrix": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        }

    field_acc: dict[str, dict[str, float]] = {}
    doc_outcomes = []
    by_tier: dict[str, dict[str, int]] = {}

    for record in records:
        prediction = record.get("prediction", {})
        ground_truth = record.get("ground_truth", {})
        field_evals = _evaluate_fields(prediction=prediction, ground_truth=ground_truth, field_defs=field_defs)

        required_ok = all(fe.correct for fe in field_evals if fe.required)
        critical_ok = all(fe.correct for fe in field_evals if fe.critical)
        evidence_required = [fe for fe in field_evals if fe.critical and fe.evidence_required]
        if evidence_required:
            evidence_coverage = sum(1 for fe in evidence_required if fe.evidence_ok) / len(evidence_required)
        else:
            evidence_coverage = 1.0

        hard_consistency_ok = _consistency_hard_ok(prediction)
        expected_decision = "AUTO_APPROVED" if (required_ok and critical_ok and evidence_coverage >= evidence_threshold and hard_consistency_ok) else "NEEDS_REVIEW"
        predicted_decision = str(record.get("decision") or expected_decision)

        doc_outcomes.append(
            {
                "doc_id": record.get("doc_id"),
                "quality_tier": str(record.get("quality_tier", "UNKNOWN")).upper(),
                "required_ok": required_ok,
                "critical_ok": critical_ok,
                "evidence_coverage": round(evidence_coverage, 4),
                "hard_consistency_ok": hard_consistency_ok,
                "expected_decision": expected_decision,
                "predicted_decision": predicted_decision,
            }
        )

        tier_key = str(record.get("quality_tier", "UNKNOWN")).upper()
        tier_bucket = by_tier.setdefault(tier_key, {"count": 0, "auto_approved": 0, "needs_review": 0})
        tier_bucket["count"] += 1
        if predicted_decision == "AUTO_APPROVED":
            tier_bucket["auto_approved"] += 1
        else:
            tier_bucket["needs_review"] += 1

        for fe in field_evals:
            bucket = field_acc.setdefault(
                fe.name,
                {
                    "correct": 0.0,
                    "total": 0.0,
                    "weight_sum": 0.0,
                    "weighted_correct_sum": 0.0,
                    "evidence_required_total": 0.0,
                    "evidence_ok_total": 0.0,
                },
            )
            bucket["total"] += 1
            bucket["weight_sum"] += fe.weight
            if fe.correct:
                bucket["correct"] += 1
                bucket["weighted_correct_sum"] += fe.weight
            if fe.evidence_required:
                bucket["evidence_required_total"] += 1
                if fe.evidence_ok:
                    bucket["evidence_ok_total"] += 1

    tp = sum(1 for row in doc_outcomes if row["predicted_decision"] == "NEEDS_REVIEW" and row["expected_decision"] == "NEEDS_REVIEW")
    tn = sum(1 for row in doc_outcomes if row["predicted_decision"] == "AUTO_APPROVED" and row["expected_decision"] == "AUTO_APPROVED")
    fp = sum(1 for row in doc_outcomes if row["predicted_decision"] == "AUTO_APPROVED" and row["expected_decision"] == "NEEDS_REVIEW")
    fn = sum(1 for row in doc_outcomes if row["predicted_decision"] == "NEEDS_REVIEW" and row["expected_decision"] == "AUTO_APPROVED")

    field_metrics = {}
    for name, bucket in field_acc.items():
        total = bucket["total"] or 1.0
        weight_sum = bucket["weight_sum"] or 1.0
        evidence_total = bucket["evidence_required_total"] or 1.0
        field_metrics[name] = {
            "accuracy": round(bucket["correct"] / total, 6),
            "weighted_accuracy": round(bucket["weighted_correct_sum"] / weight_sum, 6),
            "evidence_coverage": round(bucket["evidence_ok_total"] / evidence_total, 6),
        }

    review_ratio = (tp + fn) / total_docs
    critical_false_accept_rate = fp / total_docs
    doc_pass_rate = (tn + fp) / total_docs
    doc_critical_error_rate = (fp + fn) / total_docs

    return {
        "dataset_size": total_docs,
        "field_metrics": field_metrics,
        "document_metrics": {
            "doc_pass_rate": round(doc_pass_rate, 6),
            "review_ratio": round(review_ratio, 6),
            "critical_false_accept_rate": round(critical_false_accept_rate, 6),
            "doc_critical_error_rate": round(doc_critical_error_rate, 6),
        },
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "stratification": by_tier,
        "records": doc_outcomes,
    }


def load_gold_records(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _evaluate_fields(*, prediction: dict[str, Any], ground_truth: dict[str, Any], field_defs: list[dict[str, Any]]) -> list[FieldEvaluation]:
    pred_evidence = prediction.get("field_evidence") or {}
    out = []
    for field_def in field_defs:
        metric_name = str(field_def["name"])
        key = FIELD_NAME_MAP.get(metric_name, metric_name)
        pred = prediction.get(key)
        gt = ground_truth.get(key)
        correct = _match_values(
            pred=pred,
            gt=gt,
            field_type=field_def.get("type"),
            match=(field_def.get("match") or {}).get("type"),
            abs_tol=float((field_def.get("match") or {}).get("abs_tol", 0.01)),
        )
        evidence_ok = bool(pred_evidence.get(key))
        out.append(
            FieldEvaluation(
                name=metric_name,
                canonical_key=key,
                required=bool(field_def.get("required", False)),
                critical=bool(field_def.get("critical", False)),
                weight=float(field_def.get("weight", 1.0)),
                evidence_required=bool(field_def.get("evidence_required", False)),
                correct=correct,
                predicted_present=pred is not None and str(pred).strip() != "",
                gt_present=gt is not None and str(gt).strip() != "",
                evidence_ok=evidence_ok,
            )
        )
    return out


def _match_values(*, pred: Any, gt: Any, field_type: str | None, match: str | None, abs_tol: float = 0.01) -> bool:
    if gt is None:
        return pred is None or str(pred).strip() == ""
    if pred is None:
        return False

    if match in {"numeric_with_tolerance"} or field_type in {"money", "number"}:
        p = _to_float(pred)
        g = _to_float(gt)
        if p is None or g is None:
            return False
        return math.isclose(p, g, abs_tol=abs_tol)

    if match in {"date_equal"} or field_type == "date":
        p = _normalize_date(pred)
        g = _normalize_date(gt)
        return p is not None and g is not None and p == g

    p = _normalize_string(pred)
    g = _normalize_string(gt)
    return p == g


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^0-9.\-]", "", text.replace(",", ""))
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_string(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _normalize_date(value: Any) -> str | None:
    text = str(value or "").strip().replace("/", "-")
    if not text:
        return None
    parts = text.split("-")
    if len(parts) != 3:
        return None
    if len(parts[0]) == 4:
        y, m, d = parts[0], parts[1], parts[2]
    else:
        d, m, y = parts[0], parts[1], parts[2]
        if len(y) == 2:
            y = f"20{y}"
    try:
        yi = int(y)
        mi = int(m)
        di = int(d)
    except ValueError:
        return None
    if yi < 1900 or yi > 2100 or mi < 1 or mi > 12 or di < 1 or di > 31:
        return None
    return f"{yi:04d}-{mi:02d}-{di:02d}"


def _consistency_hard_ok(prediction: dict[str, Any]) -> bool:
    subtotal = _to_float(prediction.get("subtotal"))
    tax = _to_float(prediction.get("tax"))
    total = _to_float(prediction.get("total"))
    if subtotal is None or tax is None or total is None:
        return True
    return abs((subtotal + tax) - total) <= 0.02
