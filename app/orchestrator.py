from __future__ import annotations

import socket
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.audit import append_audit_event
from app.config import settings
from app.database import SessionLocal
from app.metrics import metrics
from app.repositories import count_runs_by_status, get_document, get_run, update_run_status, upsert_stage
from app.services.extraction import (
    OCRResult,
    StructuredExtractionResult,
    run_ocr,
    run_structured_extraction,
    to_json_bytes,
    validate_result,
)
from app.services.review_policy import evaluate_review_decision, status_from_decision
from app.services.storage import save_run_artifact, save_run_output

STAGES = ["PREPROCESS", "OCR", "EXTRACT", "VALIDATE", "PERSIST", "EXPORT"]
TERMINAL_STATUSES = {"SUCCESS", "WARN", "NEEDS_REVIEW", "FAILED", "CANCELLED"}
TRANSIENT_ERROR_CODES = {
    "OCR_TIMEOUT",
    "EXTRACT_TIMEOUT",
    "VALIDATE_TIMEOUT",
    "PERSIST_TIMEOUT",
    "EXPORT_TIMEOUT",
    "STORAGE_UNAVAILABLE",
    "MODEL_OOM",
}
STAGE_TIMEOUT_ERROR_CODE = {
    "PREPROCESS": "PREPROCESS_TIMEOUT",
    "OCR": "OCR_TIMEOUT",
    "EXTRACT": "EXTRACT_TIMEOUT",
    "VALIDATE": "VALIDATE_TIMEOUT",
    "PERSIST": "PERSIST_TIMEOUT",
    "EXPORT": "EXPORT_TIMEOUT",
}


class StageExecutionError(RuntimeError):
    def __init__(self, error_code: str, *, retryable: bool, detail: str | None = None):
        super().__init__(error_code)
        self.error_code = error_code
        self.retryable = retryable
        self.detail = detail


def process_run(run_id: str, worker_id: str = "api-background") -> None:
    db: Session = SessionLocal()
    try:
        run = get_run(db, run_id)
        if not run or run.status in TERMINAL_STATUSES:
            _sync_queue_depth(db)
            return
        if run.status == "RUNNING":
            _sync_queue_depth(db)
            return

        update_run_status(db, run, status="RUNNING", route_name="ocr_llm_pipeline")
        _sync_queue_depth(db)

        doc = get_document(db, run.document_id)
        if not doc:
            update_run_status(db, run, status="FAILED", error_code="DOCUMENT_NOT_FOUND", finished=True)
            metrics.inc("run_failed")
            _sync_queue_depth(db)
            return
        if doc.ingestion_status != "ACCEPTED":
            update_run_status(db, run, status="FAILED", error_code="DOCUMENT_QUARANTINED", finished=True)
            metrics.inc("run_failed")
            _sync_queue_depth(db)
            return

        context: dict[str, Any] = {
            "ocr": None,
            "extraction": None,
            "issues": [],
            "quality_status": "SUCCESS",
            "quality_reasons": [],
            "review_decision": "AUTO_APPROVED",
            "decision_log": None,
            "quality_tier": doc.quality_tier,
            "quality_score": doc.quality_score,
            "worker_id": worker_id,
        }
        run_started = time.monotonic()

        for stage in STAGES:
            _ensure_not_cancelled(db, run, stage)
            _ensure_run_not_timed_out(run_started)
            _execute_stage_with_retry(
                db=db,
                run=run,
                doc=doc,
                stage=stage,
                context=context,
                worker_id=worker_id,
                run_started=run_started,
            )

        extraction: StructuredExtractionResult = context["extraction"]
        issues: list[dict[str, Any]] = context["issues"]
        reason_codes: list[str] = context.get("quality_reasons") or []
        review_decision: str = context.get("review_decision") or "AUTO_APPROVED"
        decision_log: dict[str, Any] | None = context.get("decision_log")
        final_status = status_from_decision(decision=review_decision, issues=issues)

        update_run_status(
            db,
            run,
            status=final_status,
            model_name=extraction.model_name,
            route_name=extraction.route_name,
            review_decision=review_decision,
            review_reason_codes=reason_codes,
            decision_log=decision_log,
            result=extraction.result,
            validation_issues=issues,
            finished=True,
        )

        if final_status == "SUCCESS":
            metrics.inc("run_succeeded")
        elif final_status == "WARN":
            metrics.inc("run_warn")
        elif final_status == "NEEDS_REVIEW":
            metrics.inc("run_needs_review")

        append_audit_event(
            "run_completed",
            run_id=run.id,
            payload={
                "status": final_status,
                "model_name": extraction.model_name,
                "route_name": extraction.route_name,
                "issue_count": len(issues),
                "decision": review_decision,
                "reason_codes": reason_codes,
                "decision_log_hash": (decision_log or {}).get("inputs_snapshot", {}).get("hash_sha256"),
            },
        )

        if decision_log:
            try:
                save_run_artifact(run.id, "quality_decision_log.json", to_json_bytes(decision_log))
            except OSError:
                pass
        if reason_codes:
            try:
                save_run_artifact(run.id, "quality_reason_codes.json", to_json_bytes({"reason_codes": reason_codes}))
            except OSError:
                pass
    except StageExecutionError as exc:
        run = get_run(db, run_id)
        if run:
            if exc.error_code == "RUN_CANCELLED":
                update_run_status(db, run, status="CANCELLED", error_code=None, finished=True)
                metrics.inc("run_cancelled")
                append_audit_event("run_cancelled", run_id=run.id, payload={"error_code": exc.error_code})
            else:
                update_run_status(db, run, status="FAILED", error_code=exc.error_code, finished=True)
                metrics.inc("run_failed")
                if exc.error_code == "RUN_TIMEOUT":
                    metrics.inc("run_timed_out")
                append_audit_event("run_failed", run_id=run.id, payload={"error_code": exc.error_code})
    except Exception:  # noqa: BLE001
        run = get_run(db, run_id)
        if run:
            update_run_status(db, run, status="FAILED", error_code="UNEXPECTED_RUNTIME_ERROR", finished=True)
            append_audit_event("run_failed", run_id=run.id, payload={"error_code": "UNEXPECTED_RUNTIME_ERROR"})
        metrics.inc("run_failed")
    finally:
        _sync_queue_depth(db)
        db.close()


def _execute_stage_with_retry(
    *,
    db: Session,
    run,
    doc,
    stage: str,
    context: dict[str, Any],
    worker_id: str,
    run_started: float,
) -> None:
    max_attempts = 1 if stage in {"PREPROCESS", "VALIDATE", "EXPORT"} else max(1, settings.max_stage_attempts)

    for attempt in range(1, max_attempts + 1):
        _ensure_not_cancelled(db, run, stage)
        _ensure_run_not_timed_out(run_started)
        start = time.perf_counter()
        upsert_stage(
            db,
            run_id=run.id,
            stage_name=stage,
            status="RUNNING",
            attempt=attempt,
            started=True,
            details={"worker_id": worker_id},
        )

        try:
            details = _run_stage_with_timeout(
                stage=stage,
                run_id=run.id,
                doc=doc,
                context=context,
            )
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            stage_details = {"worker_id": worker_id, "duration_ms": duration_ms}
            if details:
                stage_details.update(details)
            upsert_stage(
                db,
                run_id=run.id,
                stage_name=stage,
                status="SUCCESS",
                attempt=attempt,
                finished=True,
                details=stage_details,
            )
            return
        except StageExecutionError as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            upsert_stage(
                db,
                run_id=run.id,
                stage_name=stage,
                status="FAILED",
                attempt=attempt,
                error_code=exc.error_code,
                finished=True,
                details={"worker_id": worker_id, "duration_ms": duration_ms, "detail": exc.detail},
            )
            if exc.retryable and attempt < max_attempts:
                metrics.inc("stage_retried")
                time.sleep(0.2 * attempt)
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            upsert_stage(
                db,
                run_id=run.id,
                stage_name=stage,
                status="FAILED",
                attempt=attempt,
                error_code="UNEXPECTED_RUNTIME_ERROR",
                finished=True,
                details={"worker_id": worker_id, "duration_ms": duration_ms, "detail": str(exc)},
            )
            raise StageExecutionError("UNEXPECTED_RUNTIME_ERROR", retryable=False, detail=str(exc)) from exc


def _run_stage_with_timeout(*, stage: str, run_id: str, doc, context: dict[str, Any]) -> dict[str, Any]:
    timeout_seconds = max(1, settings.stage_timeout_seconds)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"im-{stage.lower()}") as pool:
        fut = pool.submit(_execute_stage, stage, run_id, doc, context)
        try:
            return fut.result(timeout=timeout_seconds)
        except FutureTimeout as exc:
            raise StageExecutionError(
                STAGE_TIMEOUT_ERROR_CODE.get(stage, "STAGE_TIMEOUT"),
                retryable=stage in {"OCR", "EXTRACT", "PERSIST", "EXPORT"},
                detail=f"stage timeout after {timeout_seconds}s",
            ) from exc


def _execute_stage(stage: str, run_id: str, doc, context: dict[str, Any]) -> dict[str, Any]:
    if stage == "PREPROCESS":
        return _stage_preprocess(run_id, doc)
    if stage == "OCR":
        return _stage_ocr(run_id, doc, context)
    if stage == "EXTRACT":
        return _stage_extract(doc, context)
    if stage == "VALIDATE":
        return _stage_validate(context)
    if stage == "PERSIST":
        return _stage_persist(run_id, context)
    if stage == "EXPORT":
        return _stage_export(run_id, context)
    raise StageExecutionError("UNKNOWN_STAGE", retryable=False, detail=stage)


def _stage_preprocess(run_id: str, doc) -> dict[str, Any]:
    source = Path(doc.storage_path)
    details = {"filename": doc.filename, "size_bytes": int(doc.size_bytes)}
    if source.exists():
        details["size_bytes"] = int(source.stat().st_size)
    try:
        payload = f"preprocess_ok|filename={doc.filename}|bytes={details['size_bytes']}"
        save_run_artifact(run_id, "preprocess.txt", payload.encode("utf-8"))
    except OSError as exc:
        raise StageExecutionError("STORAGE_UNAVAILABLE", retryable=True, detail=str(exc)) from exc
    return details


def _stage_ocr(run_id: str, doc, context: dict[str, Any]) -> dict[str, Any]:
    ocr = run_ocr(doc.storage_path, doc.filename)
    context["ocr"] = ocr
    try:
        save_run_artifact(run_id, "ocr_text.txt", ocr.text.encode("utf-8"))
        save_run_artifact(run_id, "ocr_meta.json", to_json_bytes(asdict(ocr)))
    except OSError as exc:
        raise StageExecutionError("STORAGE_UNAVAILABLE", retryable=True, detail=str(exc)) from exc
    return {"provider": ocr.provider, "confidence": round(ocr.confidence, 4)}


def _stage_extract(doc, context: dict[str, Any]) -> dict[str, Any]:
    ocr: OCRResult | None = context.get("ocr")
    if not ocr:
        raise StageExecutionError("OCR_EMPTY", retryable=False, detail="OCR stage did not produce text")
    try:
        extracted = run_structured_extraction(
            text=ocr.text,
            filename=doc.filename,
            language=doc.language,
            file_path=doc.storage_path,
            ocr_confidence=ocr.confidence,
        )
    except MemoryError as exc:
        raise StageExecutionError("MODEL_OOM", retryable=True, detail=str(exc)) from exc
    context["extraction"] = extracted
    return {
        "provider": extracted.provider,
        "model_name": extracted.model_name,
        "route_name": extracted.route_name,
        "confidence": round(extracted.confidence, 4),
    }


def _stage_validate(context: dict[str, Any]) -> dict[str, Any]:
    ocr: OCRResult | None = context.get("ocr")
    extracted: StructuredExtractionResult | None = context.get("extraction")
    if not ocr or not extracted:
        raise StageExecutionError("VALIDATION_INPUT_MISSING", retryable=False)

    issues = validate_result(
        extracted.result,
        extraction_confidence=extracted.confidence,
        ocr_confidence=ocr.confidence,
    )
    decision_log = evaluate_review_decision(
        result=extracted.result,
        issues=issues,
        extraction_confidence=extracted.confidence,
        ocr_confidence=ocr.confidence,
        quality_tier=context.get("quality_tier"),
        quality_score=context.get("quality_score"),
    )
    decision = decision_log["decision"]
    reason_codes = decision_log["reason_codes"]
    quality_status = status_from_decision(decision=decision, issues=issues)
    context["issues"] = issues
    context["quality_status"] = quality_status
    context["quality_reasons"] = reason_codes
    context["review_decision"] = decision
    context["decision_log"] = decision_log
    return {
        "issue_count": len(issues),
        "quality_status": quality_status,
        "review_decision": decision,
        "quality_reason_codes": reason_codes,
    }


def _stage_persist(run_id: str, context: dict[str, Any]) -> dict[str, Any]:
    ocr: OCRResult | None = context.get("ocr")
    extracted: StructuredExtractionResult | None = context.get("extraction")
    issues: list[dict[str, Any]] = context.get("issues") or []
    quality_status: str = context.get("quality_status", "SUCCESS")
    reason_codes: list[str] = context.get("quality_reasons") or []
    review_decision: str = context.get("review_decision", "AUTO_APPROVED")
    decision_log: dict[str, Any] | None = context.get("decision_log")

    if not ocr or not extracted:
        raise StageExecutionError("PERSIST_INPUT_MISSING", retryable=False)

    payload = {
        "result": extracted.result,
        "validation_issues": issues,
        "model_name": extracted.model_name,
        "route_name": extracted.route_name,
        "ocr_provider": ocr.provider,
        "ocr_confidence": round(ocr.confidence, 4),
        "extraction_provider": extracted.provider,
        "extraction_confidence": round(extracted.confidence, 4),
        "quality_status": quality_status,
        "review_decision": review_decision,
        "quality_reason_codes": reason_codes,
        "decision_log": decision_log,
    }
    try:
        save_run_output(run_id, "result.json", to_json_bytes(payload))
    except OSError as exc:
        raise StageExecutionError("STORAGE_UNAVAILABLE", retryable=True, detail=str(exc)) from exc
    context["persisted_payload"] = payload
    return {"output": "result.json"}


def _stage_export(run_id: str, context: dict[str, Any]) -> dict[str, Any]:
    quality_status = context.get("quality_status", "SUCCESS")
    reason_codes = context.get("quality_reasons") or []
    review_decision = context.get("review_decision", "AUTO_APPROVED")
    export_summary = {
        "run_id": run_id,
        "quality_status": quality_status,
        "review_decision": review_decision,
        "quality_reason_codes": reason_codes,
        "exported_at_unix": int(time.time()),
    }
    try:
        save_run_artifact(run_id, "export_summary.json", to_json_bytes(export_summary))
    except OSError as exc:
        raise StageExecutionError("STORAGE_UNAVAILABLE", retryable=True, detail=str(exc)) from exc
    return {"export_artifact": "export_summary.json"}


def _ensure_not_cancelled(db: Session, run, stage: str) -> None:
    db.refresh(run)
    if not run.cancel_requested:
        return
    upsert_stage(
        db,
        run_id=run.id,
        stage_name=stage,
        status="CANCELLED",
        finished=True,
        details={"worker_id": socket.gethostname()},
    )
    raise StageExecutionError("RUN_CANCELLED", retryable=False, detail=f"cancelled before {stage}")


def _ensure_run_not_timed_out(run_started: float) -> None:
    elapsed = time.monotonic() - run_started
    if elapsed > max(1, settings.run_timeout_seconds):
        raise StageExecutionError("RUN_TIMEOUT", retryable=False, detail=f"elapsed={elapsed:.2f}s")


def _sync_queue_depth(db: Session) -> None:
    queued = count_runs_by_status(db, "QUEUED")
    metrics.set_queue_depth(queued)
