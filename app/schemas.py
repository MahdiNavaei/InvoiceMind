from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str


class DocumentOut(BaseModel):
    id: str
    tenant_id: str
    filename: str
    content_type: str
    size_bytes: int
    language: str
    ingestion_status: str
    quality_tier: str | None = None
    quality_score: float | None = None
    quarantine_item_id: str | None = None
    quarantine_reason_codes: list[str] | None = None
    created_at: datetime
    message: str | None = None


class RunCreateResponse(BaseModel):
    run_id: str
    status: str
    message: str


class RunStageOut(BaseModel):
    stage_name: str
    status: str
    attempt: int
    error_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunOut(BaseModel):
    run_id: str
    document_id: str
    tenant_id: str
    status: str
    model_name: str | None = None
    route_name: str | None = None
    error_code: str | None = None
    review_decision: str | None = None
    review_reason_codes: list[str] | None = None
    decision_log: dict[str, Any] | None = None
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    validation_issues: list[dict[str, Any]] | None = None
    stages: list[RunStageOut] = Field(default_factory=list)


class CancelResponse(BaseModel):
    run_id: str
    status: str
    message: str


class QuarantineItemOut(BaseModel):
    id: str
    document_id: str
    tenant_id: str
    stage: str
    status: str
    reason_codes: list[str]
    details: dict[str, Any] | None = None
    storage_path: str
    reprocess_count: int
    last_reprocessed_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class QuarantineListResponse(BaseModel):
    items: list[QuarantineItemOut]
    total: int


class QuarantineReprocessResponse(BaseModel):
    quarantine_item_id: str
    status: str
    reason_codes: list[str]
    message: str


class RunExportResponse(BaseModel):
    run_id: str
    status: str
    review_decision: str | None = None
    result: dict[str, Any] | None = None


class AuditChainVerifyResponse(BaseModel):
    valid: bool
    events_checked: int
    head_hash: str | None = None
    first_error_index: int | None = None
    error: str | None = None


class ChangeRiskRequest(BaseModel):
    changed_components: list[str]


class ChangeRiskResponse(BaseModel):
    risk_level: str
    changed_components: list[str]


class StageCapacityInput(BaseModel):
    stage: str
    service_time_ms: float
    concurrency: float


class CapacityEstimateRequest(BaseModel):
    stages: list[StageCapacityInput]
    safety_margin: float = 2.0
    infra_cost_per_hour: float = 3.0
    gpu_seconds_per_doc: float = 2.5
    cpu_seconds_per_doc: float = 1.0
    storage_cost_per_doc: float = 0.002
    review_ratio: float = 0.2
    review_minutes_per_doc: float = 1.0
    reviewer_cost_per_hour: float = 12.0


class CapacityEstimateResponse(BaseModel):
    capacity_system_docs_per_sec: float
    recommended_peak_lambda: float
    stage_capacities: list[dict[str, Any]]
    cost_per_doc: dict[str, float]
