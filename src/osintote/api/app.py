# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""OSINTote FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from osintote.__about__ import __version__
from osintote.api.routes import (
    ai,
    api_keys,
    errors,
    logs,
    recipes,
    records,
    relationships,
    reports,
    targets,
    tasks,
    webhooks,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — run migrations, init executor at startup."""
    # Run Alembic migrations on startup
    try:
        from osintote.models.database import auto_migrate

        await auto_migrate()
    except Exception:
        pass

    # Initialise executor
    from osintote.engine.executor import Executor
    from osintote.notify.notifier import Notifier

    executor = Executor(max_concurrent=4, cpu_workers=2)
    notifier = Notifier()
    executor.notifier = notifier
    await executor.start()
    tasks.set_executor(executor)
    _app.state.executor = executor
    yield
    await executor.stop()


app = FastAPI(
    title="OSINTote",
    description="Ultimate OSINT tool with AI-powered analysis, CLI + Web UI",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


app.include_router(ai.router)
app.include_router(api_keys.router)
app.include_router(errors.router)
app.include_router(logs.router)
app.include_router(recipes.router)
app.include_router(records.router)
app.include_router(relationships.router)
app.include_router(reports.router)
app.include_router(targets.router)
app.include_router(tasks.router)
app.include_router(webhooks.router)
