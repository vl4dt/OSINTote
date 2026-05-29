# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""SSE log streaming endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["Logs"])

# In-memory log collector (thread-safe via asyncio)
_log_buffer: deque[dict[str, Any]] = deque(maxlen=5000)
_listeners: list[asyncio.Queue] = []
_lock = asyncio.Lock()


class SSELogHandler(logging.Handler):
    """Handler that feeds log records into the SSE buffer and notifies listeners."""

    def emit(self, record: logging.LogRecord) -> None:
        """Format and enqueue a log record."""
        log_entry: dict[str, Any] = {
            "timestamp": self.format(record).split('"timestamp":')[1].split(",")[0].strip('" ')
            if '"timestamp"' in self.format(record)
            else "",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "pid": record.pid,
        }
        with suppress(json.JSONDecodeError, ValueError):
            json.loads(log_entry["timestamp"])

        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(_enqueue_log, log_entry)


def _enqueue_log(entry: dict[str, Any]) -> None:
    """Thread-safe enqueue of log entry."""
    _log_buffer.append(entry)
    for queue in _listeners:
        with suppress(asyncio.QueueFull):
            queue.put_nowait(entry)


async def _log_stream(
    task_id: str | None = None,
    logger_name: str | None = None,
    level: str | None = None,
) -> Any:
    """Generator that yields SSE-formatted log records."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _listeners.append(queue)
    try:
        # Yield buffered logs first
        async with _lock:
            while _log_buffer:
                entry = _log_buffer.popleft()
                if _matches(entry, task_id, logger_name, level):
                    yield f"data: {json.dumps(entry)}\n\n"
                await asyncio.sleep(0)

        # Stream new logs
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                if _matches(entry, task_id, logger_name, level):
                    yield f"data: {json.dumps(entry)}\n\n"
            except TimeoutError:
                yield ":\nping\n\n"
    finally:
        _listeners.remove(queue)


def _matches(
    entry: dict[str, Any],
    task_id: str | None,
    logger_name: str | None,
    level: str | None,
) -> bool:
    """Check if a log entry matches the filter criteria."""
    return not (
        (task_id and task_id.lower() not in entry.get("message", "").lower())
        or (logger_name and logger_name.lower() not in entry.get("logger", "").lower())
        or (level and entry.get("level") != level)
    )


@router.get("/stream")
async def log_stream(
    task_id: str | None = Query(None, description="Filter by task ID"),
    logger_name: str | None = Query(None, description="Filter by logger name"),
    level: str | None = Query(None, description="Filter by log level"),
) -> StreamingResponse:
    """Server-Sent Events log stream.

    Streams structured log records in real-time. Supports filtering by
    task ID, logger name, and log level.
    """

    async def stream_generator() -> Any:
        async for chunk in _log_stream(task_id, logger_name, level):
            yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/export")
async def export_logs(
    level: str | None = Query(None, description="Filter by log level"),
    limit: int = Query(1000, ge=1, le=10000, description="Max records to export"),
) -> list[dict[str, Any]]:
    """Export logs as JSON.

    Returns log records matching the filter, limited to `limit` records.
    """
    async with _lock:
        records = list(_log_buffer)

    if level:
        records = [r for r in records if r.get("level") == level]

    return records[:limit]
