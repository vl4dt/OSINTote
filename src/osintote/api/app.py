# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""OSINTote FastAPI application."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from osintote.__about__ import __version__


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan — run migrations at startup."""
    # Run Alembic migrations on startup
    try:
        from osintote.models.database import auto_migrate

        asyncio.run(auto_migrate())
    except Exception as e:
        yield  # Still start the app even if migrations fail
        return

    yield


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
