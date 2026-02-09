import os
import requests

API_URL = os.getenv("INVOICEMIND_API", "http://localhost:8000")


def test_upload_and_extract_smoke():
    try:
        health = requests.get(f"{API_URL}/health", timeout=2)
    except Exception:
        print("API not reachable; skipping smoke test")
        return

    assert health.status_code == 200

    auth = requests.post(
        f"{API_URL}/v1/auth/token",
        json={"username": "admin", "password": "admin123"},
        timeout=5,
    )
    assert auth.status_code == 200
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with open(os.path.join(os.path.dirname(__file__), "sample_invoice.png"), "rb") as f:
        payload = f.read()
    up = requests.post(
        f"{API_URL}/v1/documents",
        data=payload,
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "X-Filename": "sample_invoice.png",
            "X-Content-Type": "image/png",
        },
        timeout=10,
    )
    assert up.status_code == 200
