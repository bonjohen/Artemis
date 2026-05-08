"""FastAPI application factory with lifespan, static mounts, and CORS."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.web.db import close_db, init_db
from artemis_calendar.web.routes.candidates import router as candidates_router
from artemis_calendar.web.routes.clusters import router as clusters_router
from artemis_calendar.web.routes.images import router as images_router
from artemis_calendar.web.routes.lessons import router as lessons_router
from artemis_calendar.web.routes.selection import router as selection_router
from artemis_calendar.web.routes.stats import router as stats_router

STATIC_DIR = Path(__file__).parent / "static"
THUMBS_DIR = RAW_ROOT / "images" / "thumbs"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        csp = "default-src 'self'; script-src 'self' https://esm.sh; connect-src 'self' https://esm.sh"
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(app)
    yield
    close_db(app)


def create_app() -> FastAPI:
    app = FastAPI(title="Artemis Calendar", lifespan=lifespan)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8420"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(images_router)
    app.include_router(candidates_router)
    app.include_router(clusters_router)
    app.include_router(stats_router)
    app.include_router(selection_router)
    app.include_router(lessons_router)

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
