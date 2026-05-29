# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Error handling API — severity-tiered error management.

Endpoints:
    GET  /api/errors            — List errors with severity filter
    GET  /api/errors/{id}       — Get error details
    GET  /api/errors/stream     — SSE stream of new errors

Severity tiers:
    info    → toast notification
    warning → toast + banner
    error   → banner + log entry
    critical→ banner + log + desktop notification
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from osintote.models.database import get_async_session
from osintote.models.orm import Error, ErrorRead, ErrorSeverity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/errors", tags=["Errors"])

# ── SSE Error Queue ────────────────────────────────────────────────────────


_error_queue: asyncio.Queue[Error] = asyncio.Queue()
_error_listeners: list[asyncio.Queue[Error]] = []


async def _error_stream() -> AsyncGenerator[str]:
    """Generator that yields SSE-formatted error records."""
    while True:
        try:
            error = await asyncio.wait_for(_error_queue.get(), timeout=15.0)
            yield f"data: {json.dumps(error.model_dump())}\n\n"
        except TimeoutError:
            yield ":\nping\n\n"


@router.get("/stream")
async def error_stream() -> StreamingResponse:
    """Server-Sent Events error stream.

    Streams new errors in real-time. Clients can filter by severity
    on the client side (events include full error data).

    Severity tiers:
        info    → toast
        warning → toast + banner
        error   → banner + log
        critical→ banner + log + desktop notification
    """
    queue: asyncio.Queue[Error] = asyncio.Queue()
    _error_listeners.append(queue)

    try:

        async def _gen() -> AsyncGenerator[str]:
            while True:
                try:
                    error = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(error.model_dump())}\n\n"
                except TimeoutError:
                    yield ":\nping\n\n"

        return StreamingResponse(
            _gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    finally:
        _error_listeners.remove(queue)


# ── Error Publishing Helper ────────────────────────────────────────────────


async def publish_error(error: Error) -> None:
    """Publish an error to the SSE queue for real-time delivery."""
    with suppress(asyncio.QueueFull):
        _error_queue.put_nowait(error)


# ── CRUD ────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ErrorRead])
async def list_errors(
    severity: ErrorSeverity | None = Query(None),  # noqa: B008, RUF100
    task_id: str | None = Query(None, description="Filter by task ID"),  # noqa: B008, RUF100
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> list[Error]:
    """List errors with optional severity and task filters."""
    query = select(Error)
    if severity:
        query = query.where(Error.severity == severity)
    if task_id:
        query = query.where(Error.task_id == task_id)
    query = query.offset(offset).limit(limit).order_by(Error.created_at.desc())
    return list(db.exec(query).all())  # type: ignore[union-attr]


@router.get("/{error_id}", response_model=ErrorRead)
async def get_error(
    error_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Error:
    """Get an error by ID."""
    try:
        uid = UUID(error_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid error ID") from exc
    error = db.get(Error, uid)
    if error is None:
        raise HTTPException(status_code=404, detail=f"Error {error_id} not found")
    return error


# ── Error Severity Helpers ─────────────────────────────────────────────────


def severity_to_notification(severity: ErrorSeverity) -> str:
    """Map error severity to UI notification level.

    Returns one of: toast, toast+banner, banner+log, banner+log+notification
    """
    mapping = {
        ErrorSeverity.INFO: "toast",
        ErrorSeverity.WARNING: "toast+banner",
        ErrorSeverity.ERROR: "banner+log",
        ErrorSeverity.CRITICAL: "banner+log+notification",
    }
    return mapping.get(severity, "toast")


def is_critical(severity: ErrorSeverity) -> bool:
    """Check if error requires desktop notification."""
    return severity in (ErrorSeverity.CRITICAL,)


def is_blocking(severity: ErrorSeverity) -> bool:
    """Check if error blocks further execution."""
    return severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL)
