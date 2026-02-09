import os
import shutil
from pathlib import Path

os.environ["INVOICEMIND_DB_URL"] = "sqlite:///./test_quarantine.db"
os.environ["INVOICEMIND_STORAGE_ROOT"] = "./test_quarantine_storage"
os.environ["INVOICEMIND_JWT_SECRET"] = "test-secret-q"

db_path = Path("test_quarantine.db")
if db_path.exists():
    db_path.unlink()
storage_path = Path("test_quarantine_storage")
if storage_path.exists():
    shutil.rmtree(storage_path, ignore_errors=True)

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def auth_header(username: str = "admin", password: str = "admin123") -> dict:
    r = client.post("/v1/auth/token", json={"username": username, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_quarantine_lifecycle_for_invalid_mime():
    headers = auth_header()
    upload = client.post(
        "/v1/documents",
        content=b"not-an-invoice",
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "X-Filename": "bad_payload.txt",
            "X-Content-Type": "text/plain",
        },
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["ingestion_status"] in {"REJECTED", "QUARANTINED"}
    assert "UNSUPPORTED_MIME" in (body.get("quarantine_reason_codes") or [])
    quarantine_item_id = body.get("quarantine_item_id")
    assert quarantine_item_id

    runs = client.post(f"/v1/documents/{body['id']}/runs", headers=headers)
    assert runs.status_code == 409

    lst = client.get("/v1/quarantine", headers=headers)
    assert lst.status_code == 200
    payload = lst.json()
    assert payload["total"] >= 1
    ids = {item["id"] for item in payload["items"]}
    assert quarantine_item_id in ids

    item = client.get(f"/v1/quarantine/{quarantine_item_id}", headers=headers)
    assert item.status_code == 200
    assert "UNSUPPORTED_MIME" in item.json()["reason_codes"]

    reprocess = client.post(f"/v1/quarantine/{quarantine_item_id}/reprocess", headers=headers)
    assert reprocess.status_code == 200
    assert "UNSUPPORTED_MIME" in reprocess.json()["reason_codes"]
