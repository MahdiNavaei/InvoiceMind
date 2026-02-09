from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import settings

_lock = Lock()
_state = {"initialized": False, "last_hash": "GENESIS"}
_MASK_FIELDS_LOWER = {field.lower() for field in settings.audit_mask_fields}


def _log_path() -> Path:
    return Path(settings.storage_root) / "audit" / "events.log"


def _load_last_hash_from_disk(path: Path) -> str:
    events = _read_events(path)
    if not events:
        return "GENESIS"
    return str(events[-1].get("hash", "GENESIS"))


def reset_audit_state_for_tests() -> None:
    with _lock:
        _state["initialized"] = False
        _state["last_hash"] = "GENESIS"


def append_audit_event(event_type: str, *, run_id: str | None = None, payload: dict[str, Any] | None = None) -> str | None:
    if not settings.audit_log_enabled:
        return None

    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with _lock:
        if not _state["initialized"]:
            _state["last_hash"] = _load_last_hash_from_disk(path)
            _state["initialized"] = True

        prev_hash = str(_state["last_hash"])
        safe_payload = _mask_sensitive(payload or {})
        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "run_id": run_id,
            "payload": safe_payload,
            "prev_hash": prev_hash,
        }
        canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        event["hash"] = event_hash

        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            return None

        _state["last_hash"] = event_hash
        return event_hash


def read_audit_events(*, limit: int = 100, event_type: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
    events = _read_events(_log_path())
    if event_type:
        events = [event for event in events if str(event.get("event_type")) == event_type]
    if run_id:
        events = [event for event in events if str(event.get("run_id")) == run_id]
    if limit <= 0:
        return events
    return events[-limit:]


def verify_audit_chain() -> dict[str, Any]:
    events = _read_events(_log_path())
    prev_hash = "GENESIS"
    for idx, event in enumerate(events):
        expected_prev = str(event.get("prev_hash"))
        if expected_prev != prev_hash:
            return {
                "valid": False,
                "events_checked": idx + 1,
                "first_error_index": idx,
                "error": "prev_hash_mismatch",
            }

        copy_event = {
            "timestamp_utc": event.get("timestamp_utc"),
            "event_type": event.get("event_type"),
            "run_id": event.get("run_id"),
            "payload": event.get("payload"),
            "prev_hash": event.get("prev_hash"),
        }
        canonical = json.dumps(copy_event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        calculated_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if calculated_hash != str(event.get("hash")):
            return {
                "valid": False,
                "events_checked": idx + 1,
                "first_error_index": idx,
                "error": "hash_mismatch",
            }
        prev_hash = calculated_hash

    return {
        "valid": True,
        "events_checked": len(events),
        "head_hash": prev_hash,
    }


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:  # noqa: BLE001
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out


def _mask_sensitive(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out[k] = _mask_sensitive(v, key=str(k))
        return out
    if isinstance(value, list):
        return [_mask_sensitive(item, key=key) for item in value]
    if key and key.lower() in _MASK_FIELDS_LOWER:
        return "***REDACTED***"
    return value
