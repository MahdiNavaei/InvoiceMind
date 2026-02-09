from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from app.config import settings
from app.services.change_management import runtime_version_snapshot

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "Docs" / "Metrics_Definitions.yaml"

_metrics_cache: dict[str, Any] | None = None
_metrics_cache_mtime: float | None = None

FIELD_NAME_MAP = {
    "invoice_number": "invoice_no",
    "invoice_date": "invoice_date",
    "vendor_name": "vendor_name",
    "vendor_tax_id": "vendor_tax_id",
    "currency": "currency",
    "subtotal_amount": "subtotal",
    "tax_amount": "tax",
    "total_amount": "total",
    "due_date": "due_date",
    "payment_terms": "payment_terms",
}


def load_metrics_definitions() -> dict[str, Any]:
    global _metrics_cache
    global _metrics_cache_mtime

    mtime = METRICS_PATH.stat().st_mtime if METRICS_PATH.exists() else None
    if _metrics_cache is not None and _metrics_cache_mtime == mtime:
        return _metrics_cache

    if not METRICS_PATH.exists():
        _metrics_cache = {"version": "metrics-missing", "fields": [], "document_level": {}}
        _metrics_cache_mtime = mtime
        return _metrics_cache

    loaded = yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8")) or {}
    loaded.setdefault("fields", [])
    loaded.setdefault("document_level", {})
    _metrics_cache = loaded
    _metrics_cache_mtime = mtime
    return loaded


def evaluate_review_decision(
    *,
    result: dict[str, Any],
    issues: list[dict[str, Any]],
    extraction_confidence: float,
    ocr_confidence: float,
    quality_tier: str | None,
    quality_score: float | None,
) -> dict[str, Any]:
    metrics_def = load_metrics_definitions()
    fields = metrics_def.get("fields", [])
    thresholds = {
        "required_field_coverage_threshold": settings.required_field_coverage_threshold,
        "evidence_coverage_threshold": float(
            metrics_def.get("document_level", {}).get("evidence_coverage_threshold", settings.evidence_coverage_threshold)
        ),
        "uncertainty_threshold": settings.calibration_uncertainty_threshold,
        "risk_threshold": settings.calibration_risk_threshold,
    }

    reason_codes: list[str] = []
    gate_results: dict[str, dict[str, Any]] = {}

    # Gate 1: required fields
    required_missing = []
    required_invalid = []
    for field_def in fields:
        if not field_def.get("required", False):
            continue
        key = FIELD_NAME_MAP.get(field_def["name"], field_def["name"])
        value = result.get(key)
        if value is None or str(value).strip() == "":
            required_missing.append(key)
            continue
        if not _is_value_valid(value, field_def.get("type")):
            required_invalid.append(key)

    gate1_pass = not required_missing and not required_invalid
    gate_results["required_fields"] = {
        "passed": gate1_pass,
        "missing": required_missing,
        "invalid": required_invalid,
    }
    if required_missing:
        reason_codes.append("REQ_FIELD_MISSING")
    if required_invalid:
        reason_codes.append("REQ_FIELD_INVALID")

    # Gate 2: critical field correctness / parseability
    critical_parse_fail = []
    for field_def in fields:
        if not field_def.get("critical", False):
            continue
        key = FIELD_NAME_MAP.get(field_def["name"], field_def["name"])
        value = result.get(key)
        if value is None or str(value).strip() == "":
            continue
        if not _is_value_valid(value, field_def.get("type")):
            critical_parse_fail.append(key)

    critical_mismatch = [i for i in issues if i.get("code") in {"MISSING_REQUIRED_FIELDS", "TOTAL_MISMATCH"}]
    gate2_pass = not critical_parse_fail and not critical_mismatch
    gate_results["critical_fields"] = {
        "passed": gate2_pass,
        "parse_fail_fields": critical_parse_fail,
        "mismatch_issue_codes": [i.get("code") for i in critical_mismatch],
    }
    if critical_parse_fail:
        reason_codes.append("CRIT_FIELD_PARSE_FAIL")
    if critical_mismatch:
        reason_codes.append("CRIT_FIELD_MISMATCH")

    # Gate 3: evidence coverage on evidence-required critical fields
    evidence_required = []
    evidence_present = 0
    field_evidence = result.get("field_evidence") or {}
    for field_def in fields:
        if not field_def.get("critical", False) or not field_def.get("evidence_required", False):
            continue
        key = FIELD_NAME_MAP.get(field_def["name"], field_def["name"])
        evidence_required.append(key)
        has_evidence = bool(field_evidence.get(key))
        if has_evidence:
            evidence_present += 1
    evidence_coverage = (evidence_present / len(evidence_required)) if evidence_required else 1.0
    gate3_pass = evidence_coverage >= thresholds["evidence_coverage_threshold"]
    gate_results["evidence_coverage"] = {
        "passed": gate3_pass,
        "required_fields": evidence_required,
        "covered_fields": evidence_present,
        "coverage": round(evidence_coverage, 4),
    }
    if evidence_required and evidence_present == 0:
        reason_codes.append("EVIDENCE_MISSING")
    if not gate3_pass:
        reason_codes.append("EVIDENCE_INSUFFICIENT")

    # Gate 4: consistency rules
    hard_fail = _hard_consistency_failed(result)
    soft_fail = any(issue.get("severity") == "warning" for issue in issues)
    gate_results["consistency"] = {"passed": not hard_fail and not soft_fail, "hard_fail": hard_fail, "soft_fail": soft_fail}
    if hard_fail:
        reason_codes.append("CONSISTENCY_HARD_FAIL")
    elif soft_fail:
        reason_codes.append("CONSISTENCY_SOFT_FAIL")

    # Gate 5: low quality escalation
    quality_tier_value = (quality_tier or "MEDIUM").upper()
    uncertainty = 1.0 - min(float(extraction_confidence), float(ocr_confidence))
    risk_doc = max(1.0 - float(extraction_confidence), 1.0 - float(ocr_confidence))
    low_quality_escalation = quality_tier_value == "LOW" and uncertainty >= thresholds["uncertainty_threshold"]
    risk_exceeded = risk_doc > thresholds["risk_threshold"]
    gate_results["quality_escalation"] = {
        "passed": not low_quality_escalation and not risk_exceeded,
        "quality_tier": quality_tier_value,
        "quality_score": quality_score,
        "uncertainty": round(uncertainty, 4),
        "risk_doc": round(risk_doc, 4),
    }
    if low_quality_escalation:
        reason_codes.append("LOW_QUALITY_INPUT")
        reason_codes.append("HIGH_UNCERTAINTY")
    if risk_exceeded:
        reason_codes.append("RISK_THRESHOLD_EXCEEDED")

    decision = "NEEDS_REVIEW" if reason_codes else "AUTO_APPROVED"
    reason_codes = _dedupe_in_order(reason_codes)
    inputs_snapshot = _make_inputs_snapshot(
        result=result,
        extraction_confidence=extraction_confidence,
        ocr_confidence=ocr_confidence,
        quality_tier=quality_tier_value,
        quality_score=quality_score,
    )

    version_snapshot = runtime_version_snapshot()
    return {
        "decision": decision,
        "reason_codes": reason_codes,
        "inputs_snapshot": inputs_snapshot,
        "versions": {
            "metrics_version": metrics_def.get("version", "metrics-unknown"),
            "prompt_version": version_snapshot["versions"]["prompt_version"],
            "template_version": version_snapshot["versions"]["template_version"],
            "routing_version": version_snapshot["versions"]["routing_version"],
            "policy_version": version_snapshot["versions"]["policy_version"],
            "model_version": version_snapshot["versions"]["model_version"],
            "model_runtime": version_snapshot["runtime"]["model_runtime"],
            "model_quantization": version_snapshot["runtime"]["model_quantization"],
            "config_hashes": version_snapshot["artifact_hashes"],
        },
        "thresholds": thresholds,
        "gate_results": gate_results,
    }


def status_from_decision(*, decision: str, issues: list[dict[str, Any]]) -> str:
    if decision == "NEEDS_REVIEW":
        return "NEEDS_REVIEW"
    if any(issue.get("severity") == "warning" for issue in issues):
        return "WARN"
    return "SUCCESS"


def _hard_consistency_failed(result: dict[str, Any]) -> bool:
    subtotal = _to_float(result.get("subtotal"))
    tax = _to_float(result.get("tax"))
    total = _to_float(result.get("total"))
    currency = str(result.get("currency") or "").upper().strip()

    if currency and currency not in settings.allowed_currencies:
        return True
    if subtotal is None or tax is None or total is None:
        return False
    return abs((subtotal + tax) - total) > 0.02


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _is_value_valid(value: Any, expected_type: str | None) -> bool:
    if expected_type is None:
        return True
    if expected_type in {"money", "number"}:
        return _to_float(value) is not None
    if expected_type == "date":
        text = str(value).strip()
        if len(text) != 10:
            return False
        parts = text.split("-")
        if len(parts) != 3:
            return False
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        except ValueError:
            return False
        return 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31
    if expected_type == "string":
        return str(value).strip() != ""
    return True


def _dedupe_in_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _make_inputs_snapshot(
    *,
    result: dict[str, Any],
    extraction_confidence: float,
    ocr_confidence: float,
    quality_tier: str,
    quality_score: float | None,
) -> dict[str, Any]:
    focus = {
        "invoice_no": result.get("invoice_no"),
        "invoice_date": result.get("invoice_date"),
        "vendor_name": result.get("vendor_name"),
        "currency": result.get("currency"),
        "total": result.get("total"),
        "extraction_confidence": round(float(extraction_confidence), 4),
        "ocr_confidence": round(float(ocr_confidence), 4),
        "quality_tier": quality_tier,
        "quality_score": None if quality_score is None else round(float(quality_score), 4),
    }
    canonical = json.dumps(focus, sort_keys=True, ensure_ascii=False)
    return {
        "hash_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "signals": focus,
    }
