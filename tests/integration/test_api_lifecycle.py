import os
import base64
import shutil
import time
from pathlib import Path

os.environ["INVOICEMIND_DB_URL"] = "sqlite:///./test_invoicemind.db"
os.environ["INVOICEMIND_STORAGE_ROOT"] = "./test_storage"
os.environ["INVOICEMIND_JWT_SECRET"] = "test-secret"

db_path = Path("test_invoicemind.db")
if db_path.exists():
    db_path.unlink()
storage_path = Path("test_storage")
if storage_path.exists():
    shutil.rmtree(storage_path, ignore_errors=True)

from fastapi.testclient import TestClient

from app.main import create_app
from app.config import settings
import app.orchestrator as orchestrator


client = TestClient(create_app())


def auth_header(username: str = "admin", password: str = "admin123") -> dict:
    r = client.post("/v1/auth/token", json={"username": username, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def valid_png_payload() -> bytes:
    return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z6wAAAABJRU5ErkJggg==")


def test_full_run_lifecycle():
    headers = auth_header()
    payload = valid_png_payload()
    up = client.post(
        "/v1/documents",
        content=payload,
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "X-Filename": "sample_invoice.png",
            "X-Content-Type": "image/png",
        },
    )
    assert up.status_code == 200
    doc_id = up.json()["id"]

    r = client.post(f"/v1/documents/{doc_id}/runs", headers={**headers, "Idempotency-Key": "idem-1"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]

    # idempotency check
    r2 = client.post(f"/v1/documents/{doc_id}/runs", headers={**headers, "Idempotency-Key": "idem-1"})
    assert r2.status_code == 200
    assert r2.json()["run_id"] == run_id

    # poll for completion
    deadline = time.time() + 8
    state = "QUEUED"
    while time.time() < deadline:
        g = client.get(f"/v1/runs/{run_id}", headers=headers)
        assert g.status_code == 200
        state = g.json()["status"]
        if state in {"SUCCESS", "WARN", "FAILED", "CANCELLED", "NEEDS_REVIEW"}:
            break
        time.sleep(0.2)
    assert state in {"SUCCESS", "WARN", "NEEDS_REVIEW"}

    replay = client.post(f"/v1/runs/{run_id}/replay", headers=headers)
    assert replay.status_code == 200


def test_cancel_flow():
    headers = auth_header()
    payload = valid_png_payload()
    up = client.post(
        "/v1/documents",
        content=payload,
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "X-Filename": "sample_invoice2.png",
            "X-Content-Type": "image/png",
        },
    )
    doc_id = up.json()["id"]

    run = client.post(f"/v1/documents/{doc_id}/runs", headers=headers)
    run_id = run.json()["run_id"]

    c = client.post(f"/v1/runs/{run_id}/cancel", headers=headers)
    assert c.status_code == 200


def test_backpressure_rejects_when_queue_is_full():
    headers = auth_header()
    old_mode = settings.execution_mode
    old_reject = settings.queue_reject_depth
    old_warn = settings.queue_warn_depth

    object.__setattr__(settings, "execution_mode", "worker")
    object.__setattr__(settings, "queue_reject_depth", 1)
    object.__setattr__(settings, "queue_warn_depth", 0)

    try:
        sample = valid_png_payload()
        up1 = client.post(
            "/v1/documents",
            content=sample,
            headers={
                **headers,
                "Content-Type": "application/octet-stream",
                "X-Filename": "bp_1.png",
                "X-Content-Type": "image/png",
            },
        )
        up2 = client.post(
            "/v1/documents",
            content=sample,
            headers={
                **headers,
                "Content-Type": "application/octet-stream",
                "X-Filename": "bp_2.png",
                "X-Content-Type": "image/png",
            },
        )
        assert up1.status_code == 200
        assert up2.status_code == 200

        r1 = client.post(f"/v1/documents/{up1.json()['id']}/runs", headers=headers)
        assert r1.status_code == 200

        r2 = client.post(f"/v1/documents/{up2.json()['id']}/runs", headers=headers)
        assert r2.status_code == 429

        # drain queued run manually so this test does not leave shared state behind
        orchestrator.process_run(r1.json()["run_id"], "test-backpressure")
    finally:
        object.__setattr__(settings, "execution_mode", old_mode)
        object.__setattr__(settings, "queue_reject_depth", old_reject)
        object.__setattr__(settings, "queue_warn_depth", old_warn)


def test_retry_on_transient_ocr_failure():
    headers = auth_header()
    sample = valid_png_payload()
    up = client.post(
        "/v1/documents",
        content=sample,
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "X-Filename": "retry_ocr.png",
            "X-Content-Type": "image/png",
        },
    )
    assert up.status_code == 200

    original_run_ocr = orchestrator.run_ocr
    state = {"attempt": 0}

    def flaky_run_ocr(file_path: str, filename: str | None = None):
        if state["attempt"] == 0:
            state["attempt"] += 1
            raise orchestrator.StageExecutionError("OCR_TIMEOUT", retryable=True, detail="simulated transient timeout")
        return original_run_ocr(file_path, filename)

    orchestrator.run_ocr = flaky_run_ocr
    try:
        run_resp = client.post(f"/v1/documents/{up.json()['id']}/runs", headers=headers)
        assert run_resp.status_code == 200
        run_id = run_resp.json()["run_id"]

        deadline = time.time() + 8
        while time.time() < deadline:
            g = client.get(f"/v1/runs/{run_id}", headers=headers)
            assert g.status_code == 200
            state_now = g.json()["status"]
            if state_now in {"SUCCESS", "WARN", "NEEDS_REVIEW", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.2)

        data = client.get(f"/v1/runs/{run_id}", headers=headers).json()
        assert data["status"] in {"SUCCESS", "WARN", "NEEDS_REVIEW"}
        ocr_attempts = [s for s in data["stages"] if s["stage_name"] == "OCR"]
        assert len(ocr_attempts) >= 2
    finally:
        orchestrator.run_ocr = original_run_ocr
