from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.audit import read_audit_events, verify_audit_chain
from app.schemas import (
    AuditChainVerifyResponse,
    CapacityEstimateRequest,
    CapacityEstimateResponse,
    ChangeRiskRequest,
    ChangeRiskResponse,
)
from app.security import require_roles
from app.services.capacity import estimate_capacity, estimate_cost_per_doc
from app.services.change_management import classify_change_risk, runtime_version_snapshot

router = APIRouter(prefix="/v1", tags=["governance"])


@router.get("/audit/verify", response_model=AuditChainVerifyResponse)
def audit_verify(user: dict = Depends(require_roles("Admin", "Auditor"))):
    return AuditChainVerifyResponse(**verify_audit_chain())


@router.get("/audit/events")
def audit_events(
    limit: int = Query(default=100, ge=1, le=1000),
    event_type: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    user: dict = Depends(require_roles("Admin", "Auditor")),
):
    return {"items": read_audit_events(limit=limit, event_type=event_type, run_id=run_id)}


@router.get("/governance/runtime-versions")
def runtime_versions(user: dict = Depends(require_roles("Admin", "Auditor", "Approver"))):
    return runtime_version_snapshot()


@router.post("/governance/change-risk", response_model=ChangeRiskResponse)
def change_risk(payload: ChangeRiskRequest, user: dict = Depends(require_roles("Admin", "Auditor", "Approver"))):
    risk = classify_change_risk(payload.changed_components)
    return ChangeRiskResponse(risk_level=risk, changed_components=payload.changed_components)


@router.post("/governance/capacity-estimate", response_model=CapacityEstimateResponse)
def capacity_estimate(payload: CapacityEstimateRequest, user: dict = Depends(require_roles("Admin", "Auditor"))):
    capacity = estimate_capacity([stage.model_dump() for stage in payload.stages], safety_margin=payload.safety_margin)
    cost = estimate_cost_per_doc(
        infra_cost_per_hour=payload.infra_cost_per_hour,
        gpu_seconds_per_doc=payload.gpu_seconds_per_doc,
        cpu_seconds_per_doc=payload.cpu_seconds_per_doc,
        storage_cost_per_doc=payload.storage_cost_per_doc,
        review_ratio=payload.review_ratio,
        review_minutes_per_doc=payload.review_minutes_per_doc,
        reviewer_cost_per_hour=payload.reviewer_cost_per_hour,
    )
    return CapacityEstimateResponse(
        capacity_system_docs_per_sec=capacity["capacity_system_docs_per_sec"],
        recommended_peak_lambda=capacity["recommended_peak_lambda"],
        stage_capacities=capacity["stage_capacities"],
        cost_per_doc=cost,
    )
