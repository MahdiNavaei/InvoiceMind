from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.database import get_db
from app.i18n import pick_lang, t
from app.metrics import metrics
from app.rate_limit import rate_limit_dependency
from app.repositories import (
    create_document,
    create_quarantine_item,
    get_document,
    update_document_ingestion,
)
from app.schemas import DocumentOut
from app.security import require_roles
from app.services.extraction import detect_language
from app.services.quality_contract import evaluate_ingestion_contract
from app.services.storage import save_quarantine_document, save_quarantine_metadata, save_raw_document

router = APIRouter(prefix="/v1", tags=["documents"])


@router.post("/documents", response_model=DocumentOut, dependencies=[Depends(rate_limit_dependency)])
def upload_document(
    payload: bytes = Body(..., media_type="application/octet-stream"),
    filename: str = Header(alias="X-Filename"),
    content_type: str = Header(default="application/octet-stream", alias="X-Content-Type"),
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    tenant_id = user["tenant_id"]
    contract = evaluate_ingestion_contract(payload=payload, filename=filename, content_type=content_type)

    doc = create_document(
        db,
        tenant_id=tenant_id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(payload),
        storage_path="pending",
        language=detect_language(filename),
        ingestion_status="ACCEPTED" if contract.decision == "ACCEPT" else contract.decision,
        quality_tier=contract.quality_tier,
        quality_score=contract.quality_score,
    )

    quarantine_item_id: str | None = None
    if contract.decision == "ACCEPT":
        path = save_raw_document(doc.id, filename, payload)
        update_document_ingestion(
            db,
            doc,
            storage_path=path,
            ingestion_status="ACCEPTED",
            quality_tier=contract.quality_tier,
            quality_score=contract.quality_score,
        )
        message = t("upload_ok", lang)
    else:
        quarantine_path = save_quarantine_document(tenant_id, doc.id, filename, payload)
        save_quarantine_metadata(
            quarantine_path,
            payload=json.dumps(
                {
                    "stage": contract.stage,
                    "reason_codes": contract.reason_codes,
                    "details": contract.details,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
        )
        item = create_quarantine_item(
            db,
            document_id=doc.id,
            tenant_id=tenant_id,
            stage=contract.stage,
            status=contract.quarantine_status or "QUARANTINED_UNKNOWN",
            reason_codes=contract.reason_codes or ["QUARANTINED_UNKNOWN"],
            storage_path=quarantine_path,
            details=contract.details,
        )
        quarantine_item_id = item.id
        metrics.inc("quarantine_created")
        update_document_ingestion(
            db,
            doc,
            storage_path=quarantine_path,
            ingestion_status="QUARANTINED" if contract.decision == "QUARANTINE" else "REJECTED",
            quality_tier=contract.quality_tier,
            quality_score=contract.quality_score,
        )
        append_audit_event(
            "document_quarantined",
            payload={
                "document_id": doc.id,
                "tenant_id": tenant_id,
                "reason_codes": contract.reason_codes,
                "status": item.status,
            },
        )
        message = t("upload_quarantined", lang) if contract.decision == "QUARANTINE" else t("upload_rejected", lang)

    db.refresh(doc)
    return DocumentOut(
        id=doc.id,
        tenant_id=doc.tenant_id,
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        language=doc.language,
        ingestion_status=doc.ingestion_status,
        quality_tier=doc.quality_tier,
        quality_score=doc.quality_score,
        quarantine_item_id=quarantine_item_id,
        quarantine_reason_codes=contract.reason_codes or None,
        created_at=doc.created_at,
        message=message,
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document_by_id(
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver", "Viewer", "Auditor")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    doc = get_document(db, document_id, tenant_id=user["tenant_id"])
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("doc_not_found", lang))

    return DocumentOut(
        id=doc.id,
        tenant_id=doc.tenant_id,
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        language=doc.language,
        ingestion_status=doc.ingestion_status,
        quality_tier=doc.quality_tier,
        quality_score=doc.quality_score,
        created_at=doc.created_at,
    )
