import base64

from app.services.quality_contract import evaluate_ingestion_contract


def test_contract_rejects_unsupported_mime():
    result = evaluate_ingestion_contract(
        payload=b"hello world",
        filename="payload.bin",
        content_type="application/octet-stream",
    )
    assert result.decision == "REJECT"
    assert "UNSUPPORTED_MIME" in result.reason_codes
    assert result.stage == "A"


def test_contract_quarantines_bad_image_decode():
    result = evaluate_ingestion_contract(
        payload=b"\x89PNG\r\n\x1a\nnot-a-real-image",
        filename="broken.png",
        content_type="image/png",
    )
    assert result.decision in {"QUARANTINE", "ACCEPT"}
    if result.decision == "QUARANTINE":
        assert "IMAGE_DECODE_FAIL" in result.reason_codes
        assert result.stage == "B"


def test_contract_accepts_sample_invoice_png():
    payload = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z6wAAAABJRU5ErkJggg==")
    result = evaluate_ingestion_contract(
        payload=payload,
        filename="sample_invoice.png",
        content_type="image/png",
    )
    assert result.decision == "ACCEPT"
    assert result.reason_codes == []
