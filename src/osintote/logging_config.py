# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Structured JSON logging for OSINTote.

Provides a ``get_logger`` factory that returns loggers emitting JSON lines
to the console and an optional rotating file, plus an ``SSELogHandler``
for streaming structured log events over Server-Sent Events.

All log records carry: timestamp, level, logger name, task_id, stage,
message, and an arbitrary ``meta`` dict (JSON-serialised).

Usage::

    from osintote.logging_config import get_logger

    log = get_logger("osintote.cli.init")
    log.info("Project initialised", task_id="abc-123", stage="setup")
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(obj: Any) -> str:
    """Serialize an object to a JSON string, handling non-serialisable types."""
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except TypeError, ValueError:
        return json.dumps(str(obj), ensure_ascii=False)


def _iso_now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Fields emitted:
        timestamp, level, logger, task_id, stage, message, meta, pid,
        filename, lineno.
    """

    def __init__(
        self,
        extra_fields: list[str] | None = None,
        include_meta: bool = True,
        indent: int | None = None,
    ) -> None:
        super().__init__()
        self._extra_fields = extra_fields or []
        self._include_meta = include_meta
        self._indent = indent

    # noinspection PyMethodOverriding
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        ts = getattr(record, "timestamp", _iso_now())
        task_id = getattr(record, "task_id", None)
        stage = getattr(record, "stage", None)

        obj: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "pid": getattr(record, "pid", os.getpid()),
            "filename": record.filename,
            "lineno": record.lineno,
        }

        if task_id is not None:
            obj["task_id"] = task_id
        if stage is not None:
            obj["stage"] = stage

        # Merge extra attributes
        for field in self._extra_fields:
            val = getattr(record, field, None)
            if val is not None:
                obj[field] = val

        # meta: merge record.__dict__ keys that look like free-form extras
        if self._include_meta:
            meta_keys = {"task_id", "stage", "timestamp"}
            meta: dict[str, Any] = {}
            for key, val in record.__dict__.items():
                if key in meta_keys or key in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "message",
                    "getMessage",
                    "pid",
                    "recorded",
                    "task",
                    "stage",
                    "timestamp",
                    "task_id",
                    "logger",
                }:
                    continue
                if not key.startswith("_"):
                    try:
                        json.dumps(val)  # only include JSON-safe values
                    except TypeError, ValueError:
                        continue
                    meta[key] = val
            if meta:
                obj["meta"] = meta

        indent = self._indent
        return json.dumps(obj, default=str, ensure_ascii=False, indent=indent)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class SSELogHandler(logging.Handler):
    """Stream structured log events over Server-Sent Events.

    Each log record is emitted as a ``data:`` line followed by an ``id``
    and a blank separator, compatible with the JavaScript
    ``EventSource`` API.

    Usage (FastAPI / Starlette)::

        from fastapi import Request
        from osintote.logging_config import SSELogHandler, get_logger

        log = get_logger("sse", sse=True)

        async def stream(request: Request):
            async def event_stream():
                log.info("Session started", stage="sse")
                while not request.state.stopping:
                    yield f"event: log\\ndata: ...\\n\\n"
                    await asyncio.sleep(1)
            return EventResponse(event_stream())
    """

    def __init__(self) -> None:
        super().__init__()
        self._queue: list[dict[str, Any]] = []
        self._lock: object | None = None  # placeholder; no threading in uvicorn

    def emit(self, record: logging.LogRecord) -> None:
        """Build an SSE-formatted string and store it."""
        try:
            ts = getattr(record, "timestamp", _iso_now())
            task_id = getattr(record, "task_id", None)
            stage = getattr(record, "stage", None)
            obj = {
                "event": "log",
                "data": {
                    "timestamp": ts,
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                },
            }
            if task_id is not None:
                obj["data"]["task_id"] = task_id
            if stage is not None:
                obj["data"]["stage"] = stage
            self._queue.append(obj)
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        data = list(self._queue)
        self._queue.clear()
        for entry in data:
            _sse_line(entry)

    def get_events(self) -> list[dict[str, Any]]:
        """Return and clear queued SSE events."""
        events = list(self._queue)
        self._queue.clear()
        return events


def _sse_line(entry: dict[str, Any]) -> None:
    """Write a single SSE frame to stdout (for dev / pipe usage)."""
    event_type = entry.get("event", "log")
    data_obj = entry.get("data", {})
    data_json = json.dumps(data_obj, default=str, ensure_ascii=False)
    print(f"event: {event_type}")
    print(f"data: {data_json}")
    print()
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def _ensure_log_dir(log_dir: Path) -> Path:
    """Create the log directory if it doesn't exist."""
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_logger(
    name: str,
    level: int = logging.DEBUG,
    task_id: str | None = None,
    stage: str | None = None,
    log_file: str | Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 3,
) -> logging.Logger:
    """Create or retrieve a structured logger for *name*.

    Parameters
    ----------
    name : str
        Logger name (e.g. ``"osintote.cli.init"``).
    level : int
        Logging level (default ``DEBUG``).
    task_id : str | None
        Optional task identifier injected into every record.
    stage : str | None
        Optional stage name injected into every record.
    log_file : str | Path | None
        Path to a rotating log file.  If ``None``, only console output is
        used.  Defaults to ``.osintote/logs/osintote.jsonl``.
    max_bytes : int
        Maximum size of a single log file before rotation.
    backup_count : int
        Number of rotated backup files to retain.

    Returns
    -------
    logging.Logger
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Ensure log directory exists before checking for duplicate handlers
    if log_file is not None:
        _ensure_log_dir(Path(log_file).parent)

    # Avoid adding duplicate handlers
    if logger.handlers:
        # Update level and inject task_id/stage on existing handlers
        for handler in logger.handlers:
            if hasattr(handler, "_task_id"):
                handler._task_id = task_id  # type: ignore[attr-defined]
            if hasattr(handler, "_stage"):
                handler._stage = stage  # type: ignore[attr-defined]
        return logger

    task_id = task_id or str(uuid.uuid4())[:8]
    stage = stage or ""

    fmt = JSONFormatter(
        extra_fields=["task_id", "stage"],
        include_meta=True,
        indent=None,
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    console._task_id = task_id  # type: ignore[attr-defined]
    console._stage = stage  # type: ignore[attr-defined]
    logger.addHandler(console)

    # File handler (rotating)
    if log_file is not None:
        log_path = Path(log_file)
        _ensure_log_dir(log_path.parent)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        file_handler._task_id = task_id  # type: ignore[attr-defined]
        file_handler._stage = stage  # type: ignore[attr-defined]
        logger.addHandler(file_handler)

    # SSE handler
    sse = SSELogHandler()
    sse.setLevel(level)
    sse.setFormatter(fmt)
    sse._task_id = task_id  # type: ignore[attr-defined]
    sse._stage = stage  # type: ignore[attr-defined]
    logger.addHandler(sse)

    return logger


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

# Application-wide default logger
DEFAULT_LOG_FILE = Path(".osintote/logs/osintote.jsonl")


def setup_logging(
    level: int = logging.DEBUG,
    log_file: str | Path | None = None,
) -> logging.Logger:
    """Initialise the root OSINTote logger and return it.

    Call this early in ``osintote serve`` or ``osintote init`` to get
    consistent structured logging across the application.
    """
    lf = log_file or str(DEFAULT_LOG_FILE)
    root = get_logger(
        "osintote",
        level=level,
        log_file=lf,
    )
    # Also set the root logger level for third-party libs
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return root
