from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

SUPPORTED_IMAGE_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",
}


@dataclass
class IngestionContractResult:
    decision: str
    stage: str
    reason_codes: list[str]
    details: dict[str, Any] = field(default_factory=dict)
    quality_score: float | None = None
    quality_tier: str | None = None

    @property
    def quarantine_status(self) -> str | None:
        if self.decision != "QUARANTINE":
            return None
        if self.stage == "A":
            if any(code in self.reason_codes for code in {"SECURITY_POLICY_VIOLATION"}):
                return "QUARANTINED_SECURITY_POLICY"
            return "QUARANTINED_UNKNOWN"
        if self.stage == "B":
            return "QUARANTINED_PARSE_FAIL"
        if self.stage == "C":
            return "QUARANTINED_LOW_QUALITY"
        if self.stage == "D":
            return "QUARANTINED_SCHEMA_FAIL"
        return "QUARANTINED_UNKNOWN"


def evaluate_ingestion_contract(
    *,
    payload: bytes,
    filename: str,
    content_type: str,
) -> IngestionContractResult:
    content_hash = hashlib.sha256(payload).hexdigest()
    details: dict[str, Any] = {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(payload),
        "content_hash": content_hash,
        "limits": {
            "max_upload_size_bytes": settings.max_upload_size_bytes,
            "max_pdf_pages": settings.max_pdf_pages,
            "max_xlsx_rows_per_sheet": settings.max_xlsx_rows_per_sheet,
        },
    }

    stage_a = _validate_stage_a(payload=payload, content_type=content_type, details=details)
    if stage_a:
        return stage_a

    stage_b = _validate_stage_b(payload=payload, content_type=content_type, details=details)
    if stage_b:
        return stage_b

    quality_score, quality_tier, quality_reasons, quality_details = _validate_stage_c(
        payload=payload,
        content_type=content_type,
    )
    details.update(quality_details)
    details["quality_score"] = quality_score
    details["quality_tier"] = quality_tier
    if quality_reasons and settings.quarantine_low_quality:
        return IngestionContractResult(
            decision="QUARANTINE",
            stage="C",
            reason_codes=quality_reasons,
            details=details,
            quality_score=quality_score,
            quality_tier=quality_tier,
        )
    if quality_reasons:
        details["quality_reason_codes"] = quality_reasons

    return IngestionContractResult(
        decision="ACCEPT",
        stage="C",
        reason_codes=[],
        details=details,
        quality_score=quality_score,
        quality_tier=quality_tier,
    )


def _validate_stage_a(*, payload: bytes, content_type: str, details: dict[str, Any]) -> IngestionContractResult | None:
    if content_type not in settings.allowed_mime_types:
        return IngestionContractResult(
            decision="REJECT",
            stage="A",
            reason_codes=["UNSUPPORTED_MIME"],
            details=details,
        )

    if len(payload) > settings.max_upload_size_bytes:
        return IngestionContractResult(
            decision="QUARANTINE",
            stage="A",
            reason_codes=["FILE_TOO_LARGE"],
            details=details,
        )

    if len(payload) < 4:
        return IngestionContractResult(
            decision="QUARANTINE",
            stage="A",
            reason_codes=["FILE_CORRUPT"],
            details=details,
        )

    return None


def _validate_stage_b(*, payload: bytes, content_type: str, details: dict[str, Any]) -> IngestionContractResult | None:
    if content_type == "application/pdf":
        if not payload.startswith(b"%PDF"):
            return IngestionContractResult(
                decision="QUARANTINE",
                stage="B",
                reason_codes=["PDF_PARSE_FAIL"],
                details=details,
            )
        if b"/Encrypt" in payload[:65536]:
            return IngestionContractResult(
                decision="QUARANTINE",
                stage="B",
                reason_codes=["ENCRYPTED_PDF_UNSUPPORTED"],
                details=details,
            )
        page_count = payload.count(b"/Type /Page")
        details["pdf_page_count_estimate"] = page_count
        if page_count > settings.max_pdf_pages:
            return IngestionContractResult(
                decision="QUARANTINE",
                stage="B",
                reason_codes=["TOO_MANY_PAGES"],
                details=details,
            )
        return None

    if content_type in {"image/png", "image/jpeg", "image/webp"}:
        if not _is_image_readable(payload):
            return IngestionContractResult(
                decision="QUARANTINE",
                stage="B",
                reason_codes=["IMAGE_DECODE_FAIL"],
                details=details,
            )
        return None

    if content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        parse_result = _validate_xlsx(payload)
        details.update(parse_result["details"])
        if parse_result["reason_codes"]:
            return IngestionContractResult(
                decision="QUARANTINE",
                stage="B",
                reason_codes=parse_result["reason_codes"],
                details=details,
            )
        return None

    return None


def _validate_stage_c(*, payload: bytes, content_type: str) -> tuple[float, str, list[str], dict[str, Any]]:
    quality_score = 0.8
    reasons: list[str] = []
    details: dict[str, Any] = {}

    if content_type in {"image/png", "image/jpeg", "image/webp"}:
        width, height = _read_image_dimensions(payload)
        if width and height:
            megapixels = (width * height) / 1_000_000.0
            quality_score = min(1.0, max(0.2, 0.25 + (megapixels / 2.0)))
            details["image_dimensions"] = {"width": width, "height": height}
        else:
            quality_score = 0.75
        if quality_score < 0.55:
            reasons.append("OCR_PRECHECK_LOW_CONF")
        if width and height and min(width, height) < 700:
            reasons.append("LOW_RESOLUTION")
            quality_score = min(quality_score, 0.5)

    elif content_type == "application/pdf":
        quality_score = 0.75
    elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        quality_score = 0.85

    if quality_score >= 0.8:
        tier = "HIGH"
    elif quality_score >= 0.55:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    return quality_score, tier, sorted(set(reasons)), details


def _is_image_readable(payload: bytes) -> bool:
    magic = payload[:12]
    if not any(magic.startswith(sig) for sig in SUPPORTED_IMAGE_MAGIC):
        return False
    try:
        from PIL import Image  # type: ignore
    except Exception:  # noqa: BLE001
        return True

    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
        return True
    except Exception:  # noqa: BLE001
        # In local deployments we allow OCR fallback even when image parsers are strict.
        return True


def _read_image_dimensions(payload: bytes) -> tuple[int | None, int | None]:
    try:
        from PIL import Image  # type: ignore
    except Exception:  # noqa: BLE001
        return None, None
    try:
        with Image.open(io.BytesIO(payload)) as image:
            return int(image.width), int(image.height)
    except Exception:  # noqa: BLE001
        return None, None


def _validate_xlsx(payload: bytes) -> dict[str, Any]:
    details: dict[str, Any] = {"xlsx_sheet_count": 0}
    reason_codes: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            names = zf.namelist()
            if "xl/workbook.xml" not in names:
                return {"reason_codes": ["XLSX_PARSE_FAIL"], "details": details}

            sheet_files = [name for name in names if name.startswith("xl/worksheets/sheet")]
            details["xlsx_sheet_count"] = len(sheet_files)
            if not sheet_files:
                reason_codes.append("XLSX_PARSE_FAIL")

            shared_strings = {}
            if "xl/sharedStrings.xml" in names:
                details["xlsx_has_shared_strings"] = True
                shared_strings = {"count": len(zf.read("xl/sharedStrings.xml"))}
            details["xlsx_shared_strings_meta"] = shared_strings

            for sheet in sheet_files:
                xml = zf.read(sheet)
                rows = xml.count(b"<row")
                if rows > settings.max_xlsx_rows_per_sheet:
                    reason_codes.append("XLSX_PARSE_FAIL")
                    details[f"{sheet}_rows"] = rows
                    break
    except zipfile.BadZipFile:
        reason_codes.append("XLSX_PARSE_FAIL")
    except Exception:  # noqa: BLE001
        reason_codes.append("XLSX_PARSE_FAIL")

    return {"reason_codes": sorted(set(reason_codes)), "details": details}
