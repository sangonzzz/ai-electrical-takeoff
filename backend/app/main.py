"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, health, jobs, sheets
from app.services.queue import close_arq_pool
from app.services.storage import ensure_dirs
from app.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    ensure_dirs(settings)
    yield
    await close_arq_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Electrical Takeoff API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(jobs.router)
    app.include_router(sheets.router)
    return app


app = create_app()
