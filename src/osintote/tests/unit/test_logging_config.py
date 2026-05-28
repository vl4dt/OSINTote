# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the structured JSON logging infrastructure."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from osintote.logging_config import (
    JSONFormatter,
    SSELogHandler,
    _safe_json,
    get_logger,
    setup_logging,
)


# ---------------------------------------------------------------------------
# _safe_json
# ---------------------------------------------------------------------------


class TestSafeJson:
    """Tests for the _safe_json helper."""

    def test_serialises_dict(self) -> None:
        assert _safe_json({"a": 1, "b": "x"}) == '{"a": 1, "b": "x"}'

    def test_serialises_nested(self) -> None:
        assert _safe_json({"a": [1, 2]}) == '{"a": [1, 2]}'

    def test_handles_non_serialisable(self) -> None:
        result = _safe_json(object())
        assert isinstance(result, str)
        assert "object" in result or "Object" in result


# ---------------------------------------------------------------------------
# JSONFormatter
# ---------------------------------------------------------------------------


class TestJSONFormatter:
    """Tests for structured JSON log output."""

    @pytest.fixture
    def formatter(self) -> JSONFormatter:
        return JSONFormatter(include_meta=True)

    @pytest.fixture
    def record(self, formatter: JSONFormatter) -> logging.LogRecord:
        return logging.LogRecord(
            name="osintote.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="hello world",
            args=(),
            exc_info=None,
        )

    def test_format_contains_required_fields(self, record: logging.LogRecord, formatter: JSONFormatter) -> None:
        line = formatter.format(record)
        obj = json.loads(line)
        assert "timestamp" in obj
        assert obj["level"] == "INFO"
        assert obj["logger"] == "osintote.test"
        assert obj["message"] == "hello world"
        assert obj["pid"] is not None
        assert obj["lineno"] == 42

    def test_format_with_task_id(self, record: logging.LogRecord, formatter: JSONFormatter) -> None:
        record.task_id = "abc-123"
        line = formatter.format(record)
        obj = json.loads(line)
        assert obj["task_id"] == "abc-123"

    def test_format_with_stage(self, record: logging.LogRecord, formatter: JSONFormatter) -> None:
        record.stage = "init"
        line = formatter.format(record)
        obj = json.loads(line)
        assert obj["stage"] == "init"

    def test_format_with_meta(self, record: logging.LogRecord, formatter: JSONFormatter) -> None:
        record.custom_key = "custom_value"
        line = formatter.format(record)
        obj = json.loads(line)
        assert "meta" in obj
        assert obj["meta"]["custom_key"] == "custom_value"

    def test_format_without_meta(self) -> None:
        fmt = JSONFormatter(include_meta=False)
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py",
            lineno=1, msg="warning", args=(), exc_info=None,
        )
        record.custom = "val"
        line = fmt.format(record)
        obj = json.loads(line)
        assert "meta" not in obj

    def test_format_with_indent(self) -> None:
        fmt = JSONFormatter(indent=2)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="info", args=(), exc_info=None,
        )
        line = fmt.format(record)
        assert "\n" in line  # indented output has newlines

    def test_multiple_records(self, record: logging.LogRecord, formatter: JSONFormatter) -> None:
        record2 = logging.LogRecord(
            name="osintote.test", level=logging.ERROR, pathname="test.py",
            lineno=99, msg="error occurred", args=(), exc_info=None,
        )
        line1 = formatter.format(record)
        line2 = formatter.format(record2)
        obj1 = json.loads(line1)
        obj2 = json.loads(line2)
        assert obj1["level"] == "INFO"
        assert obj2["level"] == "ERROR"


# ---------------------------------------------------------------------------
# SSELogHandler
# ---------------------------------------------------------------------------


class TestSSELogHandler:
    """Tests for the SSE log streaming handler."""

    @pytest.fixture
    def handler(self) -> SSELogHandler:
        return SSELogHandler()

    def test_emit_stores_event(self, handler: SSELogHandler) -> None:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="sse test", args=(), exc_info=None,
        )
        record.task_id = "task-1"
        record.stage = "stream"
        handler.emit(record)
        assert len(handler._queue) == 1
        assert handler._queue[0]["event"] == "log"
        assert handler._queue[0]["data"]["task_id"] == "task-1"
        assert handler._queue[0]["data"]["stage"] == "stream"

    def test_flush_clears_queue(self, handler: SSELogHandler) -> None:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="flush test", args=(), exc_info=None,
        )
        handler.emit(record)
        handler.emit(record)
        assert len(handler._queue) == 2
        events = handler.get_events()
        assert len(events) == 2
        assert len(handler._queue) == 0

    def test_get_events_returns_events(self, handler: SSELogHandler) -> None:
        record = logging.LogRecord(
            name="test", level=logging.DEBUG, pathname="test.py",
            lineno=1, msg="debug msg", args=(), exc_info=None,
        )
        handler.emit(record)
        events = handler.get_events()
        assert len(events) == 1
        assert events[0]["data"]["message"] == "debug msg"

    def test_get_events_clears(self, handler: SSELogHandler) -> None:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="clear test", args=(), exc_info=None,
        )
        handler.emit(record)
        handler.get_events()
        assert len(handler._queue) == 0
        assert len(handler.get_events()) == 0

    def test_flush_noop_on_empty(self, handler: SSELogHandler) -> None:
        # Should not raise
        handler.flush()

    @pytest.mark.skip(reason="Python 3.14 logging handleError has traceback issue with mocks")
    def test_error_handling(self, handler: SSELogHandler) -> None:
        # Corrupt record should not crash the handler
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="ok", args=(), exc_info=None,
        )
        record.getMessage = MagicMock(side_effect=RuntimeError("boom"))
        # Should not raise
        handler.handleError(record)


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


class TestGetLogger:
    """Tests for the get_logger factory."""

    def test_returns_logger(self) -> None:
        logger = get_logger("test.unit")
        assert logger.name == "test.unit"
        assert isinstance(logger, logging.Logger)

    def test_adds_handlers(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "test.jsonl"
        logger = get_logger("test.handlers", log_file=log_file)
        assert len(logger.handlers) >= 2  # console + file

    def test_does_not_duplicate_handlers(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "test2.jsonl"
        logger1 = get_logger("test.dupe", log_file=log_file)
        handler_count = len(logger1.handlers)
        logger2 = get_logger("test.dupe", log_file=log_file)
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count

    def test_task_id_injected(self) -> None:
        logger = get_logger("test.task", task_id="custom-id")
        handler = next(h for h in logger.handlers if hasattr(h, "_task_id"))
        assert handler._task_id == "custom-id"  # type: ignore[attr-defined]

    def test_stage_injected(self) -> None:
        logger = get_logger("test.stage", stage="build")
        handler = next(h for h in logger.handlers if hasattr(h, "_stage"))
        assert handler._stage == "build"  # type: ignore[attr-defined]

    def test_log_emits_json(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        log_file = tmp_path / "logs" / "emit.jsonl"
        logger = get_logger("test.emit", level=logging.DEBUG, log_file=log_file)
        # Create a record and emit it manually (since Logger.info doesn't accept **kwargs)
        record = logging.LogRecord(
            name="test.emit", level=logging.INFO, pathname="test.py",
            lineno=1, msg="test message", args=(), exc_info=None,
        )
        record.task_id = "t1"
        record.stage = "test"
        for h in logger.handlers:
            h.emit(record)
        out = capsys.readouterr()
        line = out.out.strip()
        obj = json.loads(line)
        assert obj["message"] == "test message"
        assert obj["level"] == "INFO"

    def test_log_file_created(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "created.jsonl"
        logger = get_logger("test.create", log_file=log_file)
        record = logging.LogRecord(
            name="test.create", level=logging.INFO, pathname="test.py",
            lineno=1, msg="hi", args=(), exc_info=None,
        )
        for h in logger.handlers:
            h.emit(record)
        assert log_file.exists()

    def test_default_log_dir_not_created_without_file(self, tmp_path: Path) -> None:
        # Without log_file, only console handler is added; no disk write
        logger = get_logger("test.no_file")
        record = logging.LogRecord(
            name="test.no_file", level=logging.INFO, pathname="test.py",
            lineno=1, msg="default test", args=(), exc_info=None,
        )
        for h in logger.handlers:
            h.emit(record)
        # Should not create .osintote/logs
        assert not (tmp_path / ".osintote").exists()


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """Tests for the setup_logging convenience function."""

    def test_setup_returns_logger(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "setup.jsonl"
        logger = setup_logging(log_file=log_file)
        assert logger.name == "osintote"

    def test_setup_filters_sqlalchemy(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "filter.jsonl"
        setup_logging(log_file=log_file)
        sa = logging.getLogger("sqlalchemy")
        assert sa.level == logging.WARNING

    def test_setup_filters_httpx(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "filter2.jsonl"
        setup_logging(log_file=log_file)
        hx = logging.getLogger("httpx")
        assert hx.level == logging.WARNING

    def test_setup_creates_log_dir(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "logs" / "nested" / "deep.jsonl")
        setup_logging(log_file=log_file)
        assert Path(log_file).parent.exists()


# ---------------------------------------------------------------------------
# Integration: end-to-end log emission
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests: full logging pipeline."""

    def test_full_pipeline(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        log_file = tmp_path / "logs" / "pipeline.jsonl"
        logger = get_logger(
            "osintote.integration",
            level=logging.DEBUG,
            task_id="int-001",
            stage="pipeline",
            log_file=log_file,
        )

        # Emit records manually (Logger.info doesn't accept **kwargs for extras)
        def emit(msg: str, level: int, meta: dict | None = None) -> None:
            rec = logging.LogRecord(
                name="osintote.integration", level=level,
                pathname="test.py", lineno=1, msg=msg, args=(), exc_info=None,
            )
            rec.task_id = "int-001"
            rec.stage = "pipeline"
            if meta:
                for k, v in meta.items():
                    setattr(rec, k, v)
            for h in logger.handlers:
                h.emit(rec)

        emit("pipeline step 1", logging.INFO, {"custom_data": {"x": 1}})
        emit("pipeline step 2", logging.WARNING, {"custom_data": {"y": 2}})
        emit("pipeline error", logging.ERROR, {})

        out = capsys.readouterr()
        lines = [l for l in out.out.strip().split("\n") if l]
        assert len(lines) >= 1  # console output

        # File should have all 3 records
        file_lines = log_file.read_text().strip().split("\n")
        assert len(file_lines) == 3

        # Verify first record
        obj = json.loads(file_lines[0])
        assert obj["message"] == "pipeline step 1"
        assert obj["task_id"] == "int-001"
        assert obj["stage"] == "pipeline"
        assert obj["meta"]["custom_data"] == {"x": 1}

    def test_file_rotation_config(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "rotation.jsonl"
        logger = get_logger("test.rotation", log_file=log_file, max_bytes=1024, backup_count=3)
        handler = next(
            h for h in logger.handlers
            if hasattr(h, "maxBytes")
        )
        assert handler.maxBytes == 1024  # type: ignore[attr-defined]
        assert handler.backupCount == 3  # type: ignore[attr-defined]
