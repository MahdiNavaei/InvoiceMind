from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.config import settings
from app.database import get_db
from app.i18n import pick_lang, t
from app.metrics import metrics
from app.orchestrator import process_run
from app.repositories import (
    count_runs_by_status,
    create_run,
    get_document,
    get_latest_open_quarantine_for_document,
    get_run,
    get_run_by_idempotency,
    list_run_stages,
    update_run_status,
)
from app.schemas import CancelResponse, RunCreateResponse, RunExportResponse, RunOut, RunStageOut
from app.security import require_roles

router = APIRouter(prefix="/v1", tags=["runs"])


@router.post("/documents/{document_id}/runs", response_model=RunCreateResponse)
def create_document_run(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    tenant_id = user["tenant_id"]
    doc = get_document(db, document_id, tenant_id=tenant_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("doc_not_found", lang))

    if doc.ingestion_status != "ACCEPTED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=t("doc_quarantined", lang))
    if get_latest_open_quarantine_for_document(db, document_id=document_id, tenant_id=tenant_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=t("doc_quarantined", lang))

    if idempotency_key:
        existing = get_run_by_idempotency(db, idempotency_key, tenant_id=tenant_id)
        if existing:
            metrics.set_queue_depth(count_runs_by_status(db, "QUEUED"))
            return RunCreateResponse(run_id=existing.id, status=existing.status, message=t("run_created", lang))

    queued_depth = count_runs_by_status(db, "QUEUED", tenant_id=tenant_id)
    if queued_depth >= settings.queue_reject_depth:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=t("queue_overloaded", lang))

    run = create_run(
        db,
        document_id=document_id,
        tenant_id=tenant_id,
        requested_by=user["username"],
        idempotency_key=idempotency_key,
    )
    append_audit_event(
        "run_created",
        run_id=run.id,
        payload={
            "tenant_id": tenant_id,
            "document_id": document_id,
            "requested_by": user["username"],
            "idempotency_key": idempotency_key,
        },
    )
    metrics.inc("run_created")
    metrics.set_queue_depth(count_runs_by_status(db, "QUEUED"))
    if settings.execution_mode in {"background", "hybrid"}:
        background_tasks.add_task(process_run, run.id, "api-background")

    message = t("queue_backpressure", lang) if queued_depth >= settings.queue_warn_depth else t("run_created", lang)
    return RunCreateResponse(run_id=run.id, status=run.status, message=message)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run_details(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver", "Viewer", "Auditor")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    run = get_run(db, run_id, tenant_id=user["tenant_id"])
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("run_not_found", lang))

    stages = [
        RunStageOut(
            stage_name=s.stage_name,
            status=s.status,
            attempt=s.attempt,
            error_code=s.error_code,
            started_at=s.started_at,
            finished_at=s.finished_at,
        )
        for s in list_run_stages(db, run.id)
    ]

    review_reason_codes = json.loads(run.review_reason_codes_json) if run.review_reason_codes_json else None
    decision_log = json.loads(run.decision_log_json) if run.decision_log_json else None

    return RunOut(
        run_id=run.id,
        document_id=run.document_id,
        tenant_id=run.tenant_id,
        status=run.status,
        model_name=run.model_name,
        route_name=run.route_name,
        error_code=run.error_code,
        review_decision=run.review_decision,
        review_reason_codes=review_reason_codes,
        decision_log=decision_log,
        cancel_requested=run.cancel_requested,
        created_at=run.created_at,
        updated_at=run.updated_at,
        finished_at=run.finished_at,
        result=json.loads(run.result_json) if run.result_json else None,
        validation_issues=json.loads(run.validation_issues_json) if run.validation_issues_json else None,
        stages=stages,
    )


@router.post("/runs/{run_id}/cancel", response_model=CancelResponse)
def cancel_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    run = get_run(db, run_id, tenant_id=user["tenant_id"])
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("run_not_found", lang))
    run.cancel_requested = True
    if run.status == "QUEUED":
        update_run_status(db, run, status="CANCELLED", finished=True)
        metrics.inc("run_cancelled")
        append_audit_event("run_cancelled", run_id=run.id, payload={"cancelled_before_start": True, "tenant_id": run.tenant_id})
        metrics.set_queue_depth(count_runs_by_status(db, "QUEUED"))
    else:
        db.commit()
        db.refresh(run)
        append_audit_event("run_cancel_requested", run_id=run.id, payload={"status": run.status, "tenant_id": run.tenant_id})
    return CancelResponse(run_id=run.id, status=run.status, message=t("run_cancelled", lang))


@router.post("/runs/{run_id}/replay", response_model=RunCreateResponse)
def replay_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    old = get_run(db, run_id, tenant_id=user["tenant_id"])
    if not old:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("run_not_found", lang))

    queued_depth = count_runs_by_status(db, "QUEUED", tenant_id=user["tenant_id"])
    if queued_depth >= settings.queue_reject_depth:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=t("queue_overloaded", lang))

    run = create_run(
        db,
        document_id=old.document_id,
        tenant_id=old.tenant_id,
        requested_by=user["username"],
        replay_of_run_id=old.id,
    )
    append_audit_event(
        "run_replayed",
        run_id=run.id,
        payload={"replay_of_run_id": old.id, "requested_by": user["username"], "tenant_id": old.tenant_id},
    )
    metrics.inc("run_created")
    metrics.set_queue_depth(count_runs_by_status(db, "QUEUED"))
    if settings.execution_mode in {"background", "hybrid"}:
        background_tasks.add_task(process_run, run.id, "api-background")

    message = t("queue_backpressure", lang) if queued_depth >= settings.queue_warn_depth else t("run_created", lang)
    return RunCreateResponse(run_id=run.id, status=run.status, message=message)


@router.get("/runs/{run_id}/export", response_model=RunExportResponse)
def export_run_output(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Approver", "Auditor")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    run = get_run(db, run_id, tenant_id=user["tenant_id"])
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("run_not_found", lang))
    if run.status not in {"SUCCESS", "WARN", "NEEDS_REVIEW"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run is not finalized for export")

    append_audit_event(
        "run_exported",
        run_id=run.id,
        payload={
            "tenant_id": run.tenant_id,
            "requested_by": user["username"],
            "actor_roles": user["roles"],
            "status": run.status,
        },
    )
    result_payload = json.loads(run.result_json) if run.result_json else None
    return RunExportResponse(run_id=run.id, status=run.status, review_decision=run.review_decision, result=result_payload)
