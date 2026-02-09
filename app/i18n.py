from __future__ import annotations

from typing import Dict


_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "health_ok": "Service is healthy.",
        "ready_ok": "Service is ready.",
        "upload_ok": "Document uploaded successfully.",
        "upload_quarantined": "Document quarantined due to contract validation.",
        "upload_rejected": "Document rejected due to contract policy.",
        "run_created": "Run created successfully.",
        "run_cancelled": "Run cancelled.",
        "run_not_found": "Run not found.",
        "doc_not_found": "Document not found.",
        "doc_quarantined": "Document is quarantined and cannot be processed.",
        "quarantine_not_found": "Quarantine item not found.",
        "quarantine_reprocessed": "Quarantine item reprocessed.",
        "queue_overloaded": "Queue is overloaded. Please retry later.",
        "queue_backpressure": "Run accepted under backpressure conditions.",
        "unauthorized": "Unauthorized.",
        "forbidden": "Forbidden.",
        "token_issued": "Access token issued.",
    },
    "fa": {
        "health_ok": "سرویس سالم است.",
        "ready_ok": "سرویس آماده است.",
        "upload_ok": "سند با موفقیت بارگذاری شد.",
        "upload_quarantined": "سند به‌دلیل اعتبارسنجی قرارداد کیفیت به قرنطینه منتقل شد.",
        "upload_rejected": "سند به‌دلیل سیاست قرارداد کیفیت رد شد.",
        "run_created": "اجرا با موفقیت ایجاد شد.",
        "run_cancelled": "اجرا لغو شد.",
        "run_not_found": "اجرای موردنظر پیدا نشد.",
        "doc_not_found": "سند موردنظر پیدا نشد.",
        "doc_quarantined": "سند در قرنطینه است و قابل پردازش نیست.",
        "quarantine_not_found": "آیتم قرنطینه پیدا نشد.",
        "quarantine_reprocessed": "آیتم قرنطینه دوباره پردازش شد.",
        "queue_overloaded": "صف پردازش بیش از حد شلوغ است. کمی بعد دوباره تلاش کنید.",
        "queue_backpressure": "اجرا در شرایط فشار صف پذیرفته شد.",
        "unauthorized": "عدم احراز هویت.",
        "forbidden": "دسترسی مجاز نیست.",
        "token_issued": "توکن دسترسی صادر شد.",
    },
}


def pick_lang(accept_language: str | None) -> str:
    if not accept_language:
        return "en"
    raw = accept_language.lower()
    if raw.startswith("fa"):
        return "fa"
    return "en"


def t(key: str, lang: str) -> str:
    return _MESSAGES.get(lang, _MESSAGES["en"]).get(key, key)
