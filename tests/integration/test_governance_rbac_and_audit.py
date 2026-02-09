import os
import base64
import shutil
import time
from pathlib import Path

os.environ["INVOICEMIND_DB_URL"] = "sqlite:///./test_governance.db"
os.environ["INVOICEMIND_STORAGE_ROOT"] = "./test_governance_storage"
os.environ["INVOICEMIND_JWT_SECRET"] = "test-secret-g"

db_path = Path("test_governance.db")
if db_path.exists():
    db_path.unlink()
storage_path = Path("test_governance_storage")
if storage_path.exists():
    shutil.rmtree(storage_path, ignore_errors=True)

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def auth_header(username: str, password: str) -> dict:
    resp = client.post("/v1/auth/token", json={"username": username, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def valid_png_payload() -> bytes:
    return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z6wAAAABJRU5ErkJggg==")


def _create_completed_run(admin_headers: dict) -> str:
    payload = valid_png_payload()
    up = client.post(
        "/v1/documents",
        content=payload,
        headers={
            **admin_headers,
            "Content-Type": "application/octet-stream",
            "X-Filename": "governance_invoice.png",
            "X-Content-Type": "image/png",
        },
    )
    assert up.status_code == 200
    run = client.post(f"/v1/documents/{up.json()['id']}/runs", headers=admin_headers)
    assert run.status_code == 200
    run_id = run.json()["run_id"]

    deadline = time.time() + 8
    while time.time() < deadline:
        current = client.get(f"/v1/runs/{run_id}", headers=admin_headers)
        assert current.status_code == 200
        if current.json()["status"] in {"SUCCESS", "WARN", "NEEDS_REVIEW", "FAILED", "CANCELLED"}:
            break
        time.sleep(0.2)
    return run_id


def test_governance_endpoints_and_export_rbac():
    admin = auth_header("admin", "admin123")
    viewer = auth_header("viewer", "viewer123")
    auditor = auth_header("auditor", "audit123")

    denied = client.get("/v1/audit/verify", headers=viewer)
    assert denied.status_code == 403

    verify = client.get("/v1/audit/verify", headers=auditor)
    assert verify.status_code == 200
    assert "valid" in verify.json()

    run_id = _create_completed_run(admin)
    g = client.get(f"/v1/runs/{run_id}", headers=admin)
    assert g.status_code == 200
    assert g.json()["tenant_id"] == "default"

    viewer_export = client.get(f"/v1/runs/{run_id}/export", headers=viewer)
    assert viewer_export.status_code == 403

    auditor_export = client.get(f"/v1/runs/{run_id}/export", headers=auditor)
    assert auditor_export.status_code == 200
    assert auditor_export.json()["run_id"] == run_id

    risk = client.post("/v1/governance/change-risk", headers=admin, json={"changed_components": ["model_version"]})
    assert risk.status_code == 200
    assert risk.json()["risk_level"] == "high"

    capacity = client.post(
        "/v1/governance/capacity-estimate",
        headers=auditor,
        json={
            "stages": [
                {"stage": "ocr", "service_time_ms": 500, "concurrency": 2},
                {"stage": "extract", "service_time_ms": 700, "concurrency": 1},
            ]
        },
    )
    assert capacity.status_code == 200
    assert capacity.json()["capacity_system_docs_per_sec"] > 0
