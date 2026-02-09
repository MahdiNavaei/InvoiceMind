from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from app.config import settings

ROOT = Path(__file__).resolve().parents[2]

ARTIFACT_DIRS = {
    "prompt_version": "prompts",
    "template_version": "templates",
    "routing_version": "routing",
    "policy_version": "policies",
    "model_version": "models",
}


def load_active_versions() -> dict[str, str]:
    path = ROOT / settings.config_bundle_root / "active_versions.yaml"
    if not path.exists():
        return {
            "prompt_version": settings.prompt_version,
            "template_version": settings.template_version,
            "routing_version": settings.routing_version,
            "policy_version": settings.policy_version,
            "model_version": settings.model_version,
        }
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "prompt_version": str(data.get("prompt_version", settings.prompt_version)),
        "template_version": str(data.get("template_version", settings.template_version)),
        "routing_version": str(data.get("routing_version", settings.routing_version)),
        "policy_version": str(data.get("policy_version", settings.policy_version)),
        "model_version": str(data.get("model_version", settings.model_version)),
    }


def runtime_version_snapshot() -> dict[str, Any]:
    versions = load_active_versions()
    artifact_hashes = {}
    for version_key, version_value in versions.items():
        artifact_hashes[version_key] = _hash_artifact_bundle(version_key, version_value)
    return {
        "versions": versions,
        "artifact_hashes": artifact_hashes,
        "runtime": {
            "model_runtime": settings.model_runtime,
            "model_quantization": settings.model_quantization,
            "decoding_temperature": settings.decoding_temperature,
            "decoding_top_p": settings.decoding_top_p,
        },
    }


def classify_change_risk(changed_components: list[str]) -> str:
    changed = {item.strip().lower() for item in changed_components}
    if not changed:
        return "low"

    high_risk_signals = {
        "model",
        "model_version",
        "template",
        "template_version",
        "routing_order",
        "critical_fields",
        "schema",
    }
    medium_risk_signals = {
        "prompt",
        "prompt_version",
        "routing_threshold",
        "policy",
        "policy_version",
    }

    if changed.intersection(high_risk_signals):
        return "high"
    if changed.intersection(medium_risk_signals):
        return "medium"
    return "low"


def evaluate_release_gate(
    *,
    metrics: dict[str, Any],
    baseline: dict[str, Any],
    tolerance: dict[str, float] | None = None,
) -> dict[str, Any]:
    tol = tolerance or {
        "doc_pass_rate_drop": 0.005,
        "critical_error_rate_increase": 0.002,
        "critical_false_accept_ceiling": settings.critical_false_accept_ceiling,
    }
    checks = {
        "doc_pass_rate_guard": metrics.get("doc_pass_rate", 0.0) >= (baseline.get("doc_pass_rate", 0.0) - tol["doc_pass_rate_drop"]),
        "critical_error_guard": metrics.get("doc_critical_error_rate", 1.0)
        <= (baseline.get("doc_critical_error_rate", 0.0) + tol["critical_error_rate_increase"]),
        "critical_false_accept_guard": metrics.get("critical_false_accept_rate", 1.0) <= tol["critical_false_accept_ceiling"],
    }
    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "tolerance": tol}


def _hash_artifact_bundle(version_key: str, version_value: str) -> str:
    subdir = ARTIFACT_DIRS.get(version_key)
    if not subdir:
        return "missing"
    base = ROOT / settings.config_bundle_root / subdir / version_value
    if not base.exists():
        return "missing"
    files = sorted(path for path in base.rglob("*") if path.is_file())
    if not files:
        return "missing"
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.relative_to(base).as_posix().encode("utf-8"))
        digest.update(file.read_bytes())
    return digest.hexdigest()
