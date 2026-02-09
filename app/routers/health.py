from __future__ import annotations

from fastapi import APIRouter, Header

from app.database import engine
from app.i18n import pick_lang, t
from app.metrics import metrics

router = APIRouter(tags=["health"])


@router.get("/health")
def health(accept_language: str | None = Header(default=None)):
    lang = pick_lang(accept_language)
    return {"status": "ok", "message": t("health_ok", lang)}


@router.get("/ready")
def ready(accept_language: str | None = Header(default=None)):
    lang = pick_lang(accept_language)
    with engine.connect() as _:
        pass
    return {"status": "ready", "message": t("ready_ok", lang)}


@router.get("/metrics")
def get_metrics():
    return metrics.snapshot()
