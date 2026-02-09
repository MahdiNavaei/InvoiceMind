from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import ensure_storage_dirs, settings, validate_settings
from app.database import Base, engine
from app.routers import auth, documents, governance, health, quarantine, runs


def create_app() -> FastAPI:
    validate_settings(settings)
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    ensure_storage_dirs()
    Base.metadata.create_all(bind=engine)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(runs.router)
    app.include_router(quarantine.router)
    app.include_router(governance.router)

    @app.exception_handler(Exception)
    async def global_exception_handler(_, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": str(exc),
            },
        )

    return app


app = create_app()
