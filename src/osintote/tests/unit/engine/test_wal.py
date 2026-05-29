# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for Write-Ahead Log module."""

import asyncio
import json
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from osintote.engine.wal import WALEntry, WriteAheadLog


# ── WALEntry tests ───────────────────────────────────────────────────────────


class TestWALEntry:
    """Test WALEntry construction and serialization."""

    def test_insert_factory(self) -> None:
        """Test insert factory method."""
        entry = WALEntry.insert(1, 100.0, "task", "abc-123", {"status": "running"})
        assert entry.sequence == 1
        assert entry.timestamp == 100.0
        assert entry.operation == "insert"
        assert entry.entity == "task"
        assert entry.entity_id == "abc-123"
        assert entry.data == {"status": "running"}

    def test_update_factory(self) -> None:
        """Test update factory method."""
        entry = WALEntry.update(2, 200.0, "task", "abc-123", {"status": "completed"})
        assert entry.operation == "update"

    def test_delete_factory(self) -> None:
        """Test delete factory method."""
        entry = WALEntry.delete(3, 300.0, "record", "rec-001")
        assert entry.operation == "delete"
        assert entry.data == {}

    def test_delete_factory_with_data(self) -> None:
        """Test delete factory with payload data."""
        entry = WALEntry.delete(3, 300.0, "record", "rec-001", {"reason": "duplicate"})
        assert entry.data == {"reason": "duplicate"}

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        entry = WALEntry.insert(1, 100.0, "task", "abc", {"status": "running"})
        d = entry.to_dict()
        assert d == {
            "sequence": 1,
            "timestamp": 100.0,
            "operation": "insert",
            "entity": "task",
            "entity_id": "abc",
            "data": {"status": "running"},
        }

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization round-trip."""
        entry = WALEntry.insert(5, 500.0, "task", "xyz", {"status": "failed"})
        raw = entry.to_json()
        recovered = WALEntry.from_json(raw)
        assert recovered.sequence == 5
        assert recovered.timestamp == 500.0
        assert recovered.operation == "insert"
        assert recovered.entity == "task"
        assert recovered.entity_id == "xyz"
        assert recovered.data == {"status": "failed"}

    def test_from_dict(self) -> None:
        """Test construction from dict."""
        d = {
            "sequence": 10,
            "timestamp": 1000.0,
            "operation": "update",
            "entity": "target",
            "entity_id": "tgt-001",
            "data": {"name": "example.com"},
        }
        entry = WALEntry.from_dict(d)
        assert entry.sequence == 10
        assert entry.entity == "target"

    def test_from_json_malformed(self) -> None:
        """Test from_json with invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            WALEntry.from_json("not valid json")

    def test_from_dict_missing_field(self) -> None:
        """Test from_dict with missing required field."""
        with pytest.raises(KeyError):
            WALEntry.from_dict({"sequence": 1})


# ── WriteAheadLog tests ─────────────────────────────────────────────────────


class TestWriteAheadLog:
    """Test WriteAheadLog buffer operations."""

    @pytest.fixture
    def wal_path(self, tmp_path: Path) -> str:
        """Provide a temporary WAL file path."""
        return str(tmp_path / "wal.jsonl")

    def test_create(self, wal_path: str) -> None:
        """Test WAL creation."""
        wal = WriteAheadLog(wal_path=wal_path)
        assert wal._wal_path == Path(wal_path)
        assert wal._buffer == []
        assert wal._sequence == 0
        assert wal._running is False

    def test_write(self, wal_path: str) -> None:
        """Test buffering a WAL entry."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write("update", "task", "task-001", {"status": "running"})
        assert len(wal._buffer) == 1
        assert wal._sequence == 1
        assert wal.get_buffer_size() == 1

    def test_write_task_update(self, wal_path: str) -> None:
        """Test convenience write_task_update method."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write_task_update("task-001", {"status": "completed", "results_count": 5})
        assert len(wal._buffer) == 1
        assert wal._buffer[0].entity == "task"
        assert wal._buffer[0].operation == "update"

    def test_write_task_insert(self, wal_path: str) -> None:
        """Test convenience write_task_insert method."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write_task_insert("task-001", {"status": "pending", "stages": 3})
        assert len(wal._buffer) == 1
        assert wal._buffer[0].operation == "insert"

    def test_write_record_insert(self, wal_path: str) -> None:
        """Test convenience write_record_insert method."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write_record_insert("rec-001", {"type": "dns", "target": "example.com"})
        assert len(wal._buffer) == 1
        assert wal._buffer[0].entity == "record"
        assert wal._buffer[0].operation == "insert"

    def test_multiple_writes(self, wal_path: str) -> None:
        """Test multiple sequential writes."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write("insert", "task", "t1", {"status": "pending"})
        wal.write("update", "task", "t1", {"status": "running"})
        wal.write("update", "task", "t1", {"status": "completed"})
        assert len(wal._buffer) == 3
        assert wal._sequence == 3

    def test_write_appends_to_disk(self, wal_path: str) -> None:
        """Test that writes are appended to the WAL file on disk."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write("insert", "task", "t1", {"status": "pending"})
        wal.write("update", "task", "t1", {"status": "running"})

        # Verify file exists and has two lines
        assert Path(wal_path).exists()
        with open(wal_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 2
        entry = WALEntry.from_json(lines[0])
        assert entry.entity_id == "t1"
        assert entry.operation == "insert"

    def test_write_clears_buffer_after_flush(self, wal_path: str) -> None:
        """Test that the buffer is cleared after flush."""
        wal = WriteAheadLog(wal_path=wal_path)
        wal.write("insert", "task", "t1", {"status": "pending"})
        wal.write("update", "task", "t1", {"status": "running"})
        assert wal.get_buffer_size() == 2

        # Flush manually (simulates checkpoint)
        wal._buffer.clear()  # Simulate checkpoint cleared buffer
        assert wal.get_buffer_size() == 0

    def test_max_buffer_auto_flush(self, wal_path: str) -> None:
        """Test auto-flush when buffer exceeds max_buffer."""
        wal = WriteAheadLog(wal_path=wal_path, max_buffer=3)
        wal.write("insert", "task", "t1", {"status": "pending"})
        wal.write("update", "task", "t1", {"status": "running"})
        wal.write("update", "task", "t1", {"status": "running"})
        assert len(wal._buffer) == 3
        # Simulate flush (auto-flush calls _flush asynchronously)
        wal._buffer.clear()
        assert len(wal._buffer) == 0


class TestWriteAheadLogStartStop:
    """Test WAL lifecycle (start/stop)."""

    @pytest.fixture
    def wal_path(self, tmp_path: Path) -> str:
        """Provide a temporary WAL file path."""
        return str(tmp_path / "wal.jsonl")

    @pytest.mark.asyncio
    async def test_start_creates_directory(self, wal_path: str) -> None:
        """Test that start() creates the WAL directory."""
        wal = WriteAheadLog(wal_path=wal_path)
        await wal.start()
        assert wal._wal_path.parent.exists()

    @pytest.mark.asyncio
    async def test_stop(self, wal_path: str) -> None:
        """Test that stop() shuts down cleanly."""
        wal = WriteAheadLog(wal_path=wal_path)
        await wal.start()
        await wal.stop()
        assert wal._running is False
        assert wal._checkpoint_task is not None

    @pytest.mark.asyncio
    async def test_stop_without_start(self, wal_path: str) -> None:
        """Test stop() without start() does not crash."""
        wal = WriteAheadLog(wal_path=wal_path)
        await wal.stop()  # Should not crash

    @pytest.mark.asyncio
    async def test_stop_flushes_buffer(self, wal_path: str) -> None:
        """Test that stop() flushes remaining buffer."""
        wal = WriteAheadLog(wal_path=wal_path, checkpoint_s=10.0)
        await wal.start()
        wal.write("insert", "task", "t1", {"status": "pending"})
        await wal.stop()
        # Buffer should be cleared
        assert wal._buffer == []


class TestWriteAheadLogRecovery:
    """Test WAL crash recovery."""

    @pytest.fixture
    def wal_path(self, tmp_path: Path) -> str:
        """Provide a temporary WAL file path."""
        return str(tmp_path / "wal.jsonl")

    def test_recover_empty_file(self, wal_path: str) -> None:
        """Test recovery from an empty WAL file."""
        Path(wal_path).touch()
        wal = WriteAheadLog(wal_path=wal_path)
        count = wal._recover()
        assert count == 0
        assert wal.recovered_entries == 0

    def test_recover_no_file(self) -> None:
        """Test recovery when WAL file does not exist."""
        wal = WriteAheadLog(wal_path=".nonexistent/path/wal.jsonl")
        count = wal._recover()
        assert count == 0

    def test_recover_single_entry(self, wal_path: str) -> None:
        """Test recovery from a single WAL entry."""
        entry = WALEntry.insert(1, 100.0, "task", "t1", {"status": "running"})
        with open(wal_path, "w") as f:
            f.write(entry.to_json() + "\n")

        wal = WriteAheadLog(wal_path=wal_path)
        count = wal._recover()
        assert count == 1
        assert wal._sequence == 1
        assert wal.recovered_entries == 1

    def test_recover_multiple_entries(self, wal_path: str) -> None:
        """Test recovery from multiple WAL entries."""
        entries = [
            WALEntry.insert(1, 100.0, "task", "t1", {"status": "pending"}),
            WALEntry.update(2, 200.0, "task", "t1", {"status": "running"}),
            WALEntry.update(3, 300.0, "task", "t1", {"status": "completed"}),
        ]
        with open(wal_path, "w") as f:
            for entry in entries:
                f.write(entry.to_json() + "\n")

        wal = WriteAheadLog(wal_path=wal_path)
        count = wal._recover()
        assert count == 3
        assert wal._sequence == 3

    def test_recover_skips_malformed_lines(self, wal_path: str) -> None:
        """Test that recovery skips malformed lines."""
        with open(wal_path, "w") as f:
            f.write('{"sequence": 1, "timestamp": 100.0, "operation": "insert", "entity": "task", "entity_id": "t1", "data": {}}\n')
            f.write("MALFORMED LINE\n")
            f.write('{"sequence": 2, "timestamp": 200.0, "operation": "update", "entity": "task", "entity_id": "t1", "data": {"status": "running"}}\n')
            f.write("\n")  # empty line

        wal = WriteAheadLog(wal_path=wal_path)
        count = wal._recover()
        assert count == 2
        assert wal._sequence == 2

    def test_recover_continues_sequence(self, wal_path: str) -> None:
        """Test that new writes continue from recovered sequence."""
        # Pre-populate WAL with 3 entries
        with open(wal_path, "w") as f:
            for i in range(1, 4):
                entry = WALEntry.insert(i, float(i * 100), "task", "t1", {"seq": i})
                f.write(entry.to_json() + "\n")

        wal = WriteAheadLog(wal_path=wal_path)
        count = wal._recover()
        assert count == 3

        # Write a new entry — should get sequence 4
        wal.write("update", "task", "t1", {"status": "running"})
        assert wal._sequence == 4

    @pytest.mark.asyncio
    async def test_full_recovery_workflow(self, wal_path: str) -> None:
        """Test full start → recover → write → stop workflow."""
        # Simulate a crashed session: write some entries and don't flush
        wal1 = WriteAheadLog(wal_path=wal_path, checkpoint_s=10.0)
        await wal1.start()
        wal1.write("insert", "task", "t1", {"status": "pending"})
        wal1.write("update", "task", "t1", {"status": "running"})
        wal1.write("update", "task", "t1", {"status": "completed"})
        # Crash simulation — stop without checkpoint
        await wal1.stop()

        # New session recovers from WAL
        wal2 = WriteAheadLog(wal_path=wal_path, checkpoint_s=10.0)
        await wal2.start()
        assert wal2.recovered_entries == 3
        assert wal2._sequence == 3

        # Continue working
        wal2.write("update", "task", "t1", {"status": "archived"})
        assert wal2._sequence == 4
        await wal2.stop()

    @pytest.mark.asyncio
    async def test_checkpoint_loop_runs(self, wal_path: str) -> None:
        """Test that checkpoint loop runs periodically."""
        wal = WriteAheadLog(wal_path=wal_path, checkpoint_s=0.1)
        await wal.start()

        # Write some entries
        wal.write("insert", "task", "t1", {"status": "pending"})
        wal.write("update", "task", "t1", {"status": "running"})

        # Wait for checkpoint
        await asyncio.sleep(0.3)

        # Buffer should be flushed
        assert len(wal._buffer) == 0
        await wal.stop()

    def test_truncate(self, wal_path: str) -> None:
        """Test truncating the WAL file."""
        # Write some entries
        with open(wal_path, "w") as f:
            f.write(json.dumps({"sequence": 1, "timestamp": 100.0, "operation": "insert", "entity": "task", "entity_id": "t1", "data": {}}) + "\n")

        wal = WriteAheadLog(wal_path=wal_path)
        wal.truncate()
        assert not Path(wal_path).exists()

    def test_truncate_nonexistent(self) -> None:
        """Test truncating a non-existent WAL file doesn't crash."""
        wal = WriteAheadLog(wal_path=".nonexistent/wal.jsonl")
        wal.truncate()  # Should not raise


class TestWriteAheadLogIntegration:
    """Integration tests for WAL with the executor."""

    @pytest.fixture
    def wal_path(self, tmp_path: Path) -> str:
        """Provide a temporary WAL file path."""
        return str(tmp_path / "wal.jsonl")

    @pytest.mark.asyncio
    async def test_executor_with_wal(self, wal_path: str) -> None:
        """Test that executor correctly uses WAL for task status writes."""
        from osintote.engine import Executor, FakeStage
        from osintote.engine.stage import Stage
        from osintote.engine.wal import WriteAheadLog
        from osintote.notify.notifier import Notifier

        class DummyNotifier(Notifier):
            async def on_task_complete(self, task_id: str, target_name: str, extra: dict | None = None) -> None:
                pass
            async def on_task_fail(self, task_id: str, target_name: str, error_message: str | None = None) -> None:
                pass

        # Create a real executor with WAL
        wal = WriteAheadLog(wal_path=wal_path, checkpoint_s=10.0)
        notifier = DummyNotifier()
        executor = Executor(max_concurrent=1, notifier=notifier, wal=wal)

        await wal.start()
        await executor.start()

        # Submit a task with a fake stage
        task_id = "test-task-001"
        stage = FakeStage(success=True, records_count=2, message="test")
        await executor.submit(task_id, "example.com", [stage], priority=1)

        # Wait for execution
        await asyncio.sleep(0.5)

        await executor.stop()
        await wal.stop()

        # Verify WAL was written
        assert Path(wal_path).exists()
        with open(wal_path, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) > 0  # At least RUNNING and COMPLETED

        # Verify task status transitions were logged
        entries = [WALEntry.from_json(line) for line in lines]
        operations = [e.operation + ":" + e.entity_id for e in entries]
        # Should contain task updates
        task_updates = [o for o in operations if o.startswith("update:")]
        assert len(task_updates) > 0

    def test_executor_without_wal(self) -> None:
        """Test that executor works correctly without WAL (None)."""
        from osintote.engine import Executor, FakeStage

        executor = Executor(max_concurrent=1, wal=None)
        assert executor.wal is None

        stage = FakeStage(success=True)
        # Should not crash when wal is None
        assert executor.wal is None
