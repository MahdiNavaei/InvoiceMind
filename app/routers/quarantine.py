from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.database import get_db
from app.i18n import pick_lang, t
from app.metrics import metrics
from app.repositories import (
    get_document,
    get_quarantine_item,
    list_quarantine_items,
    mark_quarantine_reprocessed,
    update_document_ingestion,
)
from app.schemas import QuarantineItemOut, QuarantineListResponse, QuarantineReprocessResponse
from app.security import require_roles
from app.services.quality_contract import evaluate_ingestion_contract
from app.services.storage import save_quarantine_document, save_quarantine_metadata, save_raw_document

router = APIRouter(prefix="/v1/quarantine", tags=["quarantine"])


def _to_item_out(item) -> QuarantineItemOut:
    return QuarantineItemOut(
        id=item.id,
        document_id=item.document_id,
        tenant_id=item.tenant_id,
        stage=item.stage,
        status=item.status,
        reason_codes=json.loads(item.reason_codes_json or "[]"),
        details=json.loads(item.details_json or "{}"),
        storage_path=item.storage_path,
        reprocess_count=item.reprocess_count,
        last_reprocessed_at=item.last_reprocessed_at,
        resolved_at=item.resolved_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=QuarantineListResponse)
def list_items(
    status_filter: str | None = Query(default=None, alias="status"),
    reason_code: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver", "Auditor")),
):
    items = list_quarantine_items(
        db,
        tenant_id=user["tenant_id"],
        status=status_filter,
        reason_code=reason_code,
        limit=limit,
    )
    out = [_to_item_out(item) for item in items]
    return QuarantineListResponse(items=out, total=len(out))


@router.get("/{item_id}", response_model=QuarantineItemOut)
def get_item(
    item_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver", "Auditor")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    item = get_quarantine_item(db, item_id, tenant_id=user["tenant_id"])
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("quarantine_not_found", lang))
    return _to_item_out(item)


@router.post("/{item_id}/reprocess", response_model=QuarantineReprocessResponse)
def reprocess_item(
    item_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_roles("Admin", "Reviewer", "Approver")),
    accept_language: str | None = Header(default=None),
):
    lang = pick_lang(accept_language)
    item = get_quarantine_item(db, item_id, tenant_id=user["tenant_id"])
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("quarantine_not_found", lang))

    document = get_document(db, item.document_id, tenant_id=user["tenant_id"])
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=t("doc_not_found", lang))

    path = Path(item.storage_path)
    if not path.exists():
        mark_quarantine_reprocessed(
            db,
            item,
            status="QUARANTINED_UNKNOWN",
            reason_codes=["FILE_CORRUPT"],
            details={"error": "missing_quarantine_file"},
            resolved=False,
        )
        return QuarantineReprocessResponse(
            quarantine_item_id=item.id,
            status=item.status,
            reason_codes=["FILE_CORRUPT"],
            message=t("quarantine_reprocessed", lang),
        )

    payload = path.read_bytes()
    contract = evaluate_ingestion_contract(
        payload=payload,
        filename=document.filename,
        content_type=document.content_type,
    )
    if contract.decision == "ACCEPT":
        raw_path = save_raw_document(document.id, document.filename, payload)
        update_document_ingestion(
            db,
            document,
            storage_path=raw_path,
            ingestion_status="ACCEPTED",
            quality_tier=contract.quality_tier,
            quality_score=contract.quality_score,
        )
        mark_quarantine_reprocessed(
            db,
            item,
            status="QUARANTINE_RESOLVED",
            reason_codes=[],
            details={"reprocess_result": "accepted"},
            resolved=True,
        )
    else:
        quarantine_path = save_quarantine_document(document.tenant_id, document.id, document.filename, payload)
        save_quarantine_metadata(
            quarantine_path,
            payload=json.dumps(
                {
                    "stage": contract.stage,
                    "reason_codes": contract.reason_codes,
                    "details": contract.details,
                    "reprocessed": True,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
        )
        update_document_ingestion(
            db,
            document,
            storage_path=quarantine_path,
            ingestion_status="QUARANTINED",
            quality_tier=contract.quality_tier,
            quality_score=contract.quality_score,
        )
        mark_quarantine_reprocessed(
            db,
            item,
            status=contract.quarantine_status or "QUARANTINED_UNKNOWN",
            reason_codes=contract.reason_codes,
            details={"reprocess_result": "still_quarantined", "stage": contract.stage},
            resolved=False,
        )

    append_audit_event(
        "quarantine_reprocessed",
        payload={
            "quarantine_item_id": item.id,
            "document_id": document.id,
            "tenant_id": document.tenant_id,
            "status": item.status,
            "reason_codes": json.loads(item.reason_codes_json or "[]"),
        },
    )
    metrics.inc("quarantine_reprocessed")

    return QuarantineReprocessResponse(
        quarantine_item_id=item.id,
        status=item.status,
        reason_codes=json.loads(item.reason_codes_json or "[]"),
        message=t("quarantine_reprocessed", lang),
    )
