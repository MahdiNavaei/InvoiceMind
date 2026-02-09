from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Document, QuarantineItem, Run, RunStage


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_document(
    db: Session,
    *,
    tenant_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
    language: str,
    ingestion_status: str = "ACCEPTED",
    quality_tier: str | None = None,
    quality_score: float | None = None,
) -> Document:
    doc = Document(
        tenant_id=tenant_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
        language=language,
        ingestion_status=ingestion_status,
        quality_tier=quality_tier,
        quality_score=quality_score,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def update_document_ingestion(
    db: Session,
    document: Document,
    *,
    storage_path: str | None = None,
    ingestion_status: str | None = None,
    quality_tier: str | None = None,
    quality_score: float | None = None,
) -> Document:
    if storage_path is not None:
        document.storage_path = storage_path
    if ingestion_status is not None:
        document.ingestion_status = ingestion_status
    if quality_tier is not None:
        document.quality_tier = quality_tier
    if quality_score is not None:
        document.quality_score = quality_score
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, document_id: str, *, tenant_id: str | None = None) -> Document | None:
    q = db.query(Document).filter(Document.id == document_id)
    if tenant_id is not None:
        q = q.filter(Document.tenant_id == tenant_id)
    return q.first()


def get_run_by_idempotency(db: Session, key: str, *, tenant_id: str | None = None) -> Run | None:
    q = db.query(Run).filter(Run.idempotency_key == key)
    if tenant_id is not None:
        q = q.filter(Run.tenant_id == tenant_id)
    return q.first()


def create_run(
    db: Session,
    *,
    document_id: str,
    tenant_id: str,
    requested_by: str,
    idempotency_key: str | None = None,
    replay_of_run_id: str | None = None,
) -> Run:
    run = Run(
        document_id=document_id,
        tenant_id=tenant_id,
        requested_by=requested_by,
        idempotency_key=idempotency_key,
        replay_of_run_id=replay_of_run_id,
        status="QUEUED",
        updated_at=now_utc(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: str, *, tenant_id: str | None = None) -> Run | None:
    q = db.query(Run).filter(Run.id == run_id)
    if tenant_id is not None:
        q = q.filter(Run.tenant_id == tenant_id)
    return q.first()


def count_runs_by_status(db: Session, status: str, *, tenant_id: str | None = None) -> int:
    q = db.query(Run).filter(Run.status == status)
    if tenant_id is not None:
        q = q.filter(Run.tenant_id == tenant_id)
    return q.count()


def count_runs_by_statuses(db: Session, statuses: list[str], *, tenant_id: str | None = None) -> int:
    if not statuses:
        return 0
    q = db.query(Run).filter(Run.status.in_(statuses))
    if tenant_id is not None:
        q = q.filter(Run.tenant_id == tenant_id)
    return q.count()


def list_queued_runs(db: Session, *, limit: int = 10) -> list[Run]:
    return (
        db.query(Run)
        .filter(Run.status == "QUEUED")
        .order_by(Run.created_at.asc())
        .limit(limit)
        .all()
    )


def list_run_stages(db: Session, run_id: str) -> list[RunStage]:
    return db.query(RunStage).filter(RunStage.run_id == run_id).order_by(RunStage.id.asc()).all()


def upsert_stage(
    db: Session,
    *,
    run_id: str,
    stage_name: str,
    status: str,
    attempt: int = 1,
    error_code: str | None = None,
    details: dict | None = None,
    started: bool = False,
    finished: bool = False,
) -> RunStage:
    stage = (
        db.query(RunStage)
        .filter(RunStage.run_id == run_id, RunStage.stage_name == stage_name, RunStage.attempt == attempt)
        .first()
    )
    if not stage:
        stage = RunStage(run_id=run_id, stage_name=stage_name, attempt=attempt)
        db.add(stage)
    stage.status = status
    stage.error_code = error_code
    stage.details_json = json.dumps(details or {}, ensure_ascii=False)
    if started and not stage.started_at:
        stage.started_at = now_utc()
    if finished:
        stage.finished_at = now_utc()
    db.commit()
    db.refresh(stage)
    return stage


def update_run_status(
    db: Session,
    run: Run,
    *,
    status: str,
    error_code: str | None = None,
    model_name: str | None = None,
    route_name: str | None = None,
    review_decision: str | None = None,
    review_reason_codes: list[str] | None = None,
    decision_log: dict | None = None,
    result: dict | None = None,
    validation_issues: list[dict] | None = None,
    finished: bool = False,
) -> Run:
    run.status = status
    run.error_code = error_code
    if model_name:
        run.model_name = model_name
    if route_name:
        run.route_name = route_name
    if review_decision is not None:
        run.review_decision = review_decision
    if review_reason_codes is not None:
        run.review_reason_codes_json = json.dumps(review_reason_codes, ensure_ascii=False)
    if decision_log is not None:
        run.decision_log_json = json.dumps(decision_log, ensure_ascii=False)
    if result is not None:
        run.result_json = json.dumps(result, ensure_ascii=False)
    if validation_issues is not None:
        run.validation_issues_json = json.dumps(validation_issues, ensure_ascii=False)
    run.updated_at = now_utc()
    if finished:
        run.finished_at = now_utc()
    db.commit()
    db.refresh(run)
    return run


def create_quarantine_item(
    db: Session,
    *,
    document_id: str,
    tenant_id: str,
    stage: str,
    status: str,
    reason_codes: list[str],
    storage_path: str,
    details: dict | None = None,
) -> QuarantineItem:
    item = QuarantineItem(
        document_id=document_id,
        tenant_id=tenant_id,
        stage=stage,
        status=status,
        reason_codes_json=json.dumps(reason_codes, ensure_ascii=False),
        details_json=json.dumps(details or {}, ensure_ascii=False),
        storage_path=storage_path,
        updated_at=now_utc(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_quarantine_item(db: Session, item_id: str, *, tenant_id: str | None = None) -> QuarantineItem | None:
    q = db.query(QuarantineItem).filter(QuarantineItem.id == item_id)
    if tenant_id is not None:
        q = q.filter(QuarantineItem.tenant_id == tenant_id)
    return q.first()


def list_quarantine_items(
    db: Session,
    *,
    tenant_id: str,
    status: str | None = None,
    reason_code: str | None = None,
    limit: int = 100,
) -> list[QuarantineItem]:
    q = db.query(QuarantineItem).filter(QuarantineItem.tenant_id == tenant_id)
    if status:
        q = q.filter(QuarantineItem.status == status)
    rows = q.order_by(QuarantineItem.created_at.desc()).limit(max(1, limit)).all()
    if not reason_code:
        return rows
    out: list[QuarantineItem] = []
    for row in rows:
        reasons = json.loads(row.reason_codes_json or "[]")
        if reason_code in reasons:
            out.append(row)
    return out


def get_latest_open_quarantine_for_document(db: Session, *, document_id: str, tenant_id: str) -> QuarantineItem | None:
    return (
        db.query(QuarantineItem)
        .filter(
            QuarantineItem.document_id == document_id,
            QuarantineItem.tenant_id == tenant_id,
            QuarantineItem.resolved_at.is_(None),
        )
        .order_by(QuarantineItem.created_at.desc())
        .first()
    )


def mark_quarantine_reprocessed(
    db: Session,
    item: QuarantineItem,
    *,
    status: str,
    reason_codes: list[str],
    details: dict | None = None,
    resolved: bool = False,
) -> QuarantineItem:
    item.status = status
    item.reason_codes_json = json.dumps(reason_codes, ensure_ascii=False)
    item.details_json = json.dumps(details or {}, ensure_ascii=False)
    item.reprocess_count += 1
    item.last_reprocessed_at = now_utc()
    item.updated_at = now_utc()
    if resolved:
        item.resolved_at = now_utc()
    db.commit()
    db.refresh(item)
    return item

