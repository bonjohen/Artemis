"""FastAPI application factory with lifespan, static mounts, and CORS."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.web.db import close_db, init_db
from artemis_calendar.web.routes.candidates import router as candidates_router
from artemis_calendar.web.routes.images import router as images_router

STATIC_DIR = Path(__file__).parent / "static"
THUMBS_DIR = RAW_ROOT / "images" / "thumbs"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(app)
    yield
    close_db(app)


def create_app() -> FastAPI:
    app = FastAPI(title="Artemis Calendar", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(images_router)
    app.include_router(candidates_router)

    # Mount thumbnail images
    if THUMBS_DIR.exists():
        app.mount("/thumbs", StaticFiles(directory=str(THUMBS_DIR)), name="thumbs")

    # Mount static assets (CSS, JS)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # SPA fallback — serve index.html for the root
    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    # Health check
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app
