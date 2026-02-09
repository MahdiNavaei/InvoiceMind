from pathlib import Path

from app import audit
from app.config import settings


def test_audit_hash_chain(tmp_path: Path):
    old_root = settings.storage_root
    old_enabled = settings.audit_log_enabled
    object.__setattr__(settings, "storage_root", str(tmp_path / "storage"))
    object.__setattr__(settings, "audit_log_enabled", True)
    audit.reset_audit_state_for_tests()

    try:
        h1 = audit.append_audit_event("run_created", run_id="r1", payload={"a": 1})
        h2 = audit.append_audit_event("run_completed", run_id="r1", payload={"status": "SUCCESS", "token": "secret-token"})
        assert h1
        assert h2

        log = tmp_path / "storage" / "audit" / "events.log"
        lines = [line for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2

        import json

        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])
        assert e2["prev_hash"] == e1["hash"]
        assert e2["payload"]["token"] == "***REDACTED***"
        verification = audit.verify_audit_chain()
        assert verification["valid"] is True
    finally:
        object.__setattr__(settings, "storage_root", old_root)
        object.__setattr__(settings, "audit_log_enabled", old_enabled)
        audit.reset_audit_state_for_tests()
