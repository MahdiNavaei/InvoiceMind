from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("INVOICEMIND_ENV", "dev")
    app_name: str = os.getenv("INVOICEMIND_APP_NAME", "InvoiceMind API")
    app_version: str = os.getenv("INVOICEMIND_APP_VERSION", "0.1.0")
    db_url: str = os.getenv("INVOICEMIND_DB_URL", "sqlite:///./invoicemind.db")
    storage_root: str = os.getenv("INVOICEMIND_STORAGE_ROOT", "app/storage")
    jwt_secret: str = os.getenv("INVOICEMIND_JWT_SECRET", "change-this-in-prod")
    jwt_alg: str = os.getenv("INVOICEMIND_JWT_ALG", "HS256")
    token_exp_minutes: int = int(os.getenv("INVOICEMIND_TOKEN_EXP_MINUTES", "120"))
    rate_limit_per_minute: int = int(os.getenv("INVOICEMIND_RATE_LIMIT_PER_MINUTE", "60"))
    default_tenant_id: str = os.getenv("INVOICEMIND_DEFAULT_TENANT_ID", "default")
    execution_mode: str = os.getenv("INVOICEMIND_EXECUTION_MODE", "background")
    queue_warn_depth: int = int(os.getenv("INVOICEMIND_QUEUE_WARN_DEPTH", "10"))
    queue_reject_depth: int = int(os.getenv("INVOICEMIND_QUEUE_REJECT_DEPTH", "25"))
    max_stage_attempts: int = int(os.getenv("INVOICEMIND_MAX_STAGE_ATTEMPTS", "2"))
    stage_timeout_seconds: int = int(os.getenv("INVOICEMIND_STAGE_TIMEOUT_SECONDS", "20"))
    run_timeout_seconds: int = int(os.getenv("INVOICEMIND_RUN_TIMEOUT_SECONDS", "120"))
    worker_poll_seconds: float = float(os.getenv("INVOICEMIND_WORKER_POLL_SECONDS", "0.75"))
    worker_batch_size: int = int(os.getenv("INVOICEMIND_WORKER_BATCH_SIZE", "4"))
    low_confidence_threshold: float = float(os.getenv("INVOICEMIND_LOW_CONFIDENCE_THRESHOLD", "0.60"))
    low_ocr_confidence_threshold: float = float(os.getenv("INVOICEMIND_LOW_OCR_CONFIDENCE_THRESHOLD", "0.55"))
    required_field_coverage_threshold: float = float(os.getenv("INVOICEMIND_REQUIRED_FIELD_COVERAGE_THRESHOLD", "0.80"))
    evidence_coverage_threshold: float = float(os.getenv("INVOICEMIND_EVIDENCE_COVERAGE_THRESHOLD", "0.90"))
    max_upload_size_bytes: int = int(os.getenv("INVOICEMIND_MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024)))
    max_pdf_pages: int = int(os.getenv("INVOICEMIND_MAX_PDF_PAGES", "50"))
    max_xlsx_rows_per_sheet: int = int(os.getenv("INVOICEMIND_MAX_XLSX_ROWS_PER_SHEET", "20000"))
    quarantine_low_quality: bool = os.getenv("INVOICEMIND_QUARANTINE_LOW_QUALITY", "false").lower() in {"1", "true", "yes", "on"}
    allowed_mime_types: tuple[str, ...] = tuple(
        part.strip()
        for part in os.getenv(
            "INVOICEMIND_ALLOWED_MIME_TYPES",
            "application/pdf,image/png,image/jpeg,image/webp,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ).split(",")
        if part.strip()
    )
    allowed_currencies: tuple[str, ...] = tuple(
        part.strip().upper() for part in os.getenv("INVOICEMIND_ALLOWED_CURRENCIES", "USD,EUR,IRR").split(",") if part.strip()
    )
    calibration_uncertainty_threshold: float = float(os.getenv("INVOICEMIND_CALIBRATION_UNCERTAINTY_THRESHOLD", "0.40"))
    calibration_risk_threshold: float = float(os.getenv("INVOICEMIND_CALIBRATION_RISK_THRESHOLD", "0.30"))
    critical_false_accept_ceiling: float = float(os.getenv("INVOICEMIND_CRITICAL_FALSE_ACCEPT_CEILING", "0.001"))
    prompt_version: str = os.getenv("INVOICEMIND_PROMPT_VERSION", "PRM-20260209-v1")
    template_version: str = os.getenv("INVOICEMIND_TEMPLATE_VERSION", "TPL-20260209-v1")
    routing_version: str = os.getenv("INVOICEMIND_ROUTING_VERSION", "RTE-20260209-v1")
    policy_version: str = os.getenv("INVOICEMIND_POLICY_VERSION", "POL-20260209-v1")
    model_version: str = os.getenv("INVOICEMIND_MODEL_VERSION", "MOD-qwen2.5-7b-instruct-20260209-v1")
    model_runtime: str = os.getenv("INVOICEMIND_MODEL_RUNTIME", "local")
    model_quantization: str = os.getenv("INVOICEMIND_MODEL_QUANTIZATION", "q4")
    decoding_temperature: float = float(os.getenv("INVOICEMIND_DECODING_TEMPERATURE", "0.1"))
    decoding_top_p: float = float(os.getenv("INVOICEMIND_DECODING_TOP_P", "0.9"))
    config_bundle_root: str = os.getenv("INVOICEMIND_CONFIG_BUNDLE_ROOT", "config")
    audit_log_enabled: bool = os.getenv("INVOICEMIND_AUDIT_LOG_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    audit_mask_fields: tuple[str, ...] = tuple(
        part.strip() for part in os.getenv("INVOICEMIND_AUDIT_MASK_FIELDS", "password,token,bank_account,tax_id").split(",") if part.strip()
    )


settings = Settings()


def ensure_storage_dirs() -> None:
    root = Path(settings.storage_root)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    (root / "audit").mkdir(parents=True, exist_ok=True)
    (root / "quarantine").mkdir(parents=True, exist_ok=True)


def validate_settings(cfg: Settings) -> None:
    valid_envs = {"local", "dev", "test", "staging", "prod", "production"}
    if cfg.environment.lower() not in valid_envs:
        raise ValueError(f"Invalid INVOICEMIND_ENV: {cfg.environment}")

    if cfg.execution_mode not in {"background", "worker", "hybrid"}:
        raise ValueError(f"Invalid INVOICEMIND_EXECUTION_MODE: {cfg.execution_mode}")

    if cfg.queue_warn_depth < 0:
        raise ValueError("INVOICEMIND_QUEUE_WARN_DEPTH must be >= 0")
    if cfg.queue_reject_depth <= cfg.queue_warn_depth:
        raise ValueError("INVOICEMIND_QUEUE_REJECT_DEPTH must be > INVOICEMIND_QUEUE_WARN_DEPTH")

    if cfg.max_stage_attempts < 1:
        raise ValueError("INVOICEMIND_MAX_STAGE_ATTEMPTS must be >= 1")
    if cfg.stage_timeout_seconds < 1:
        raise ValueError("INVOICEMIND_STAGE_TIMEOUT_SECONDS must be >= 1")
    if cfg.run_timeout_seconds < cfg.stage_timeout_seconds:
        raise ValueError("INVOICEMIND_RUN_TIMEOUT_SECONDS must be >= INVOICEMIND_STAGE_TIMEOUT_SECONDS")

    if cfg.worker_poll_seconds <= 0:
        raise ValueError("INVOICEMIND_WORKER_POLL_SECONDS must be > 0")
    if cfg.worker_batch_size < 1:
        raise ValueError("INVOICEMIND_WORKER_BATCH_SIZE must be >= 1")

    thresholds = [
        ("INVOICEMIND_LOW_CONFIDENCE_THRESHOLD", cfg.low_confidence_threshold),
        ("INVOICEMIND_LOW_OCR_CONFIDENCE_THRESHOLD", cfg.low_ocr_confidence_threshold),
        ("INVOICEMIND_REQUIRED_FIELD_COVERAGE_THRESHOLD", cfg.required_field_coverage_threshold),
        ("INVOICEMIND_EVIDENCE_COVERAGE_THRESHOLD", cfg.evidence_coverage_threshold),
        ("INVOICEMIND_CALIBRATION_UNCERTAINTY_THRESHOLD", cfg.calibration_uncertainty_threshold),
        ("INVOICEMIND_CALIBRATION_RISK_THRESHOLD", cfg.calibration_risk_threshold),
        ("INVOICEMIND_CRITICAL_FALSE_ACCEPT_CEILING", cfg.critical_false_accept_ceiling),
        ("INVOICEMIND_DECODING_TEMPERATURE", cfg.decoding_temperature),
        ("INVOICEMIND_DECODING_TOP_P", cfg.decoding_top_p),
    ]
    for name, value in thresholds:
        if value < 0 or value > 1:
            raise ValueError(f"{name} must be between 0 and 1")

    if cfg.max_upload_size_bytes <= 0:
        raise ValueError("INVOICEMIND_MAX_UPLOAD_SIZE_BYTES must be > 0")
    if cfg.max_pdf_pages <= 0:
        raise ValueError("INVOICEMIND_MAX_PDF_PAGES must be > 0")
    if cfg.max_xlsx_rows_per_sheet <= 0:
        raise ValueError("INVOICEMIND_MAX_XLSX_ROWS_PER_SHEET must be > 0")
    if not cfg.allowed_mime_types:
        raise ValueError("INVOICEMIND_ALLOWED_MIME_TYPES must not be empty")
    if not cfg.allowed_currencies:
        raise ValueError("INVOICEMIND_ALLOWED_CURRENCIES must not be empty")

    if cfg.environment.lower() in {"prod", "production"} and cfg.jwt_secret == "change-this-in-prod":
        raise ValueError("INVOICEMIND_JWT_SECRET must be changed in production")
