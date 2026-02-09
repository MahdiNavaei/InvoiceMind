import os
import shutil
from pathlib import Path

os.environ["INVOICEMIND_DB_URL"] = "sqlite:///./test_security.db"
os.environ["INVOICEMIND_STORAGE_ROOT"] = "./test_security_storage"
os.environ["INVOICEMIND_JWT_SECRET"] = "test-secret-2"
os.environ["INVOICEMIND_RATE_LIMIT_PER_MINUTE"] = "3"

db_path = Path("test_security.db")
if db_path.exists():
    db_path.unlink()
storage_path = Path("test_security_storage")
if storage_path.exists():
    shutil.rmtree(storage_path, ignore_errors=True)

from fastapi.testclient import TestClient

from app.main import create_app
from app.rate_limit import limiter


client = TestClient(create_app())


def reset_limiter() -> None:
    limiter.hits.clear()
    limiter.max_per_minute = 3


def token_for(username: str, password: str) -> str:
    r = client.post("/v1/auth/token", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_unauthorized_without_token():
    r = client.get("/v1/documents/unknown")
    assert r.status_code == 401


def test_forbidden_for_reader_on_create_run():
    reset_limiter()
    admin_token = token_for("admin", "admin123")
    sample = Path("tests/e2e/sample_invoice.png").read_bytes()
    up = client.post(
        "/v1/documents",
        content=sample,
        headers={
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/octet-stream",
            "X-Filename": "sample_invoice.png",
            "X-Content-Type": "image/png",
        },
    )
    doc_id = up.json()["id"]

    reader_token = token_for("reader", "reader123")
    r = client.post(f"/v1/documents/{doc_id}/runs", headers={"Authorization": f"Bearer {reader_token}"})
    assert r.status_code == 403


def test_rate_limit_hits():
    reset_limiter()
    token = token_for("admin", "admin123")
    payload = Path("tests/e2e/sample_invoice.png").read_bytes()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "X-Filename": "rl_sample.png",
        "X-Content-Type": "image/png",
    }
    s1 = client.post("/v1/documents", content=payload, headers=headers)
    s2 = client.post("/v1/documents", content=payload, headers=headers)
    s3 = client.post("/v1/documents", content=payload, headers=headers)
    s4 = client.post("/v1/documents", content=payload, headers=headers)
    assert s1.status_code == 200
    assert s2.status_code == 200
    assert s3.status_code in {200, 429}
    assert s4.status_code == 429


def test_bilingual_health_messages():
    en = client.get("/health", headers={"Accept-Language": "en-US"})
    fa = client.get("/health", headers={"Accept-Language": "fa-IR"})
    assert en.json()["message"] == "Service is healthy."
    assert fa.json()["message"] == "سرویس سالم است."
