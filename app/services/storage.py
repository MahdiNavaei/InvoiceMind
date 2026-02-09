from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def save_raw_document(document_id: str, filename: str, payload: bytes) -> str:
    out_dir = Path(settings.storage_root) / "raw" / document_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(payload)
    return str(out_path)


def save_quarantine_document(tenant_id: str, document_id: str, filename: str, payload: bytes) -> str:
    now = datetime.now(timezone.utc)
    out_dir = (
        Path(settings.storage_root)
        / "quarantine"
        / tenant_id
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{now.day:02d}"
        / document_id
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(payload)
    return str(out_path)


def save_quarantine_metadata(storage_path: str, payload: bytes) -> str:
    target = Path(storage_path).with_name("quarantine_meta.json")
    target.write_bytes(payload)
    return str(target)


def save_run_artifact(run_id: str, name: str, payload: bytes) -> str:
    out_dir = Path(settings.storage_root) / "runs" / run_id / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name
    out_path.write_bytes(payload)
    return str(out_path)


def save_run_output(run_id: str, name: str, payload: bytes) -> str:
    out_dir = Path(settings.storage_root) / "runs" / run_id / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name
    out_path.write_bytes(payload)
    return str(out_path)
