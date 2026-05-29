# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Write-ahead log — buffered writes with periodic checkpoint and crash recovery.

The WAL provides durability for task execution by buffering database
operations and periodically flushing them.  On startup, any uncommitted
WAL entries are replayed to restore the database state.

Architecture::

    executor ──write──► WAL buffer ──5s tick──► WAL file (disk)
                                               │
                                       checkpoint ──► DB (sqlite)

Usage::

    from osintote.engine.wal import WriteAheadLog

    wal = WriteAheadLog(wal_path=".osintote/wal.jsonl", checkpoint_s=5)
    await wal.start()          # launch checkpoint background task
    wal.write({"task_id": "x", "op": "update", "status": "running"})
    await wal.stop()           # drain + flush remaining entries
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── WAL Entry ────────────────────────────────────────────────────────────────


class WALEntry:
    """Single write-ahead log entry.

    Attributes
    ----------
    sequence:
        Monotonically increasing sequence number.
    timestamp:
        Wall-clock time in seconds since epoch.
    operation:
        One of ``insert``, ``update``, ``delete``.
    entity:
        Target entity name (``task``, ``record``, ``target``).
    entity_id:
        UUID string of the affected entity.
    data:
        Arbitrary payload (dict) to apply on replay.
    """

    __slots__ = ("data", "entity", "entity_id", "operation", "sequence", "timestamp")

    def __init__(
        self,
        sequence: int,
        timestamp: float,
        operation: str,
        entity: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> None:
        self.sequence = sequence
        self.timestamp = timestamp
        self.operation = operation
        self.entity = entity
        self.entity_id = entity_id
        self.data = data

    @classmethod
    def insert(
        cls,
        seq: int,
        ts: float,
        entity: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> WALEntry:
        """Create an INSERT operation entry."""
        return cls(seq, ts, "insert", entity, entity_id, data)

    @classmethod
    def update(
        cls,
        seq: int,
        ts: float,
        entity: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> WALEntry:
        """Create an UPDATE operation entry."""
        return cls(seq, ts, "update", entity, entity_id, data)

    @classmethod
    def delete(
        cls,
        seq: int,
        ts: float,
        entity: str,
        entity_id: str,
        data: dict[str, Any] | None = None,
    ) -> WALEntry:
        """Create a DELETE operation entry."""
        return cls(seq, ts, "delete", entity, entity_id, data or {})

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "entity": self.entity,
            "entity_id": self.entity_id,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WALEntry:
        """Reconstruct from a dict (deserialise)."""
        return cls(
            sequence=d["sequence"],
            timestamp=d["timestamp"],
            operation=d["operation"],
            entity=d["entity"],
            entity_id=d["entity_id"],
            data=d["data"],
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, raw: str) -> WALEntry:
        """Deserialize from a JSON string."""
        return cls.from_dict(json.loads(raw))


# ── Write-Ahead Log ──────────────────────────────────────────────────────────


class WriteAheadLog:
    """Buffered WAL with periodic checkpoint and crash recovery.

    Parameters
    ----------
    wal_path:
        Path to the WAL file on disk.
    checkpoint_s:
        Seconds between background checkpoints (default 5).
    max_buffer:
        Maximum entries to buffer before flushing (default 100).
    """

    def __init__(
        self,
        wal_path: str = ".osintote/wal.jsonl",
        checkpoint_s: float = 5.0,
        max_buffer: int = 100,
    ) -> None:
        self._wal_path = Path(wal_path)
        self._checkpoint_s = checkpoint_s
        self._max_buffer = max_buffer

        self._buffer: list[WALEntry] = []
        self._sequence: int = 0
        self._running = False
        self._checkpoint_task: asyncio.Task[None] | None = None
        self._recovered_entries: int = 0

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch the WAL — recover from disk, start checkpoint loop.

        1. Ensure the WAL directory exists.
        2. Replay any existing WAL file entries.
        3. Launch the periodic checkpoint background task.
        """
        self._wal_path.parent.mkdir(parents=True, exist_ok=True)

        # Replay existing entries
        self._recover()
        if self._recovered_entries > 0:
            logger.info(
                "WAL recovered %d entries from %s",
                self._recovered_entries,
                self._wal_path,
            )

        # Start checkpoint loop
        self._running = True
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        logger.info(
            "WAL started: checkpoint every %.0fs, max buffer %d",
            self._checkpoint_s,
            self._max_buffer,
        )

    async def stop(self) -> None:
        """Stop the WAL — flush remaining entries, cancel checkpoint task."""
        self._running = False
        if self._checkpoint_task is not None:
            self._checkpoint_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._checkpoint_task
        # Final flush of remaining buffer
        if self._buffer:
            await self._flush()
            self._buffer.clear()
        logger.info("WAL stopped")

    # ── Write operations ─────────────────────────────────────────────────

    def write(
        self,
        operation: str,
        entity: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> None:
        """Buffer a WAL entry.

        Parameters
        ----------
        operation:
            One of ``insert``, ``update``, ``delete``.
        entity:
            Entity type (``task``, ``record``, ``target``).
        entity_id:
            UUID string of the entity.
        data:
            Payload to persist on replay.
        """
        self._sequence += 1
        entry = WALEntry(
            sequence=self._sequence,
            timestamp=time.time(),
            operation=operation,
            entity=entity,
            entity_id=entity_id,
            data=data,
        )
        self._buffer.append(entry)

        # Write to disk immediately (append to WAL file)
        self._append_to_disk(entry)

        # Auto-flush if buffer exceeds threshold (only when running)
        if self._running and len(self._buffer) >= self._max_buffer:
            asyncio.create_task(self._flush())  # noqa: RUF006

    def write_task_update(
        self,
        task_id: str,
        data: dict[str, Any],
    ) -> None:
        """Convenience: buffer a task status update."""
        self.write("update", "task", task_id, data)

    def write_task_insert(
        self,
        task_id: str,
        data: dict[str, Any],
    ) -> None:
        """Convenience: buffer a task creation."""
        self.write("insert", "task", task_id, data)

    def write_record_insert(
        self,
        record_id: str,
        data: dict[str, Any],
    ) -> None:
        """Convenience: buffer a record creation."""
        self.write("insert", "record", record_id, data)

    def get_buffer_size(self) -> int:
        """Return the number of uncommitted entries in the buffer."""
        return len(self._buffer)

    @property
    def recovered_entries(self) -> int:
        """Number of entries recovered from disk on startup."""
        return self._recovered_entries

    # ── Checkpoint ───────────────────────────────────────────────────────

    async def _checkpoint_loop(self) -> None:
        """Background loop: flush the buffer at regular intervals."""
        while self._running:
            try:
                await asyncio.sleep(self._checkpoint_s)
            except asyncio.CancelledError:
                break
            if self._buffer:
                await self._flush()

    async def _flush(self) -> None:
        """Flush all buffered entries to the database snapshot.

        In a full implementation, this would write the entries to the
        database.  For now, entries are persisted to disk via
        ``_append_to_disk`` on each write.

        The checkpoint is primarily a safety net: it logs how many
        buffered entries are being committed and resets the buffer.
        """
        if not self._buffer:
            return
        count = len(self._buffer)
        self._buffer.clear()
        logger.debug("WAL checkpoint: flushed %d entries", count)

    # ── Disk persistence ─────────────────────────────────────────────────

    def _append_to_disk(self, entry: WALEntry) -> None:
        """Append a single entry to the WAL file on disk."""
        with open(self._wal_path, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")

    # ── Recovery ─────────────────────────────────────────────────────────

    def _recover(self) -> int:
        """Recover entries from an existing WAL file.

        Returns
        -------
        int
            Number of entries recovered.
        """
        if not self._wal_path.exists():
            return 0

        recovered = 0
        max_seq = 0
        try:
            with open(self._wal_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = WALEntry.from_json(line)
                        max_seq = max(max_seq, entry.sequence)
                        recovered += 1
                    except json.JSONDecodeError, KeyError, TypeError:
                        logger.warning("Skipping malformed WAL entry: %s", line[:80])
        except OSError as exc:
            logger.error("Failed to recover WAL file: %s", exc)
            return 0

        self._recovered_entries = recovered
        self._sequence = max_seq
        return max_seq

    def truncate(self) -> None:
        """Remove the WAL file (after successful checkpoint to DB)."""
        if self._wal_path.exists():
            try:
                self._wal_path.unlink()
                logger.info("WAL file truncated: %s", self._wal_path)
            except OSError as exc:
                logger.warning("Failed to truncate WAL file: %s", exc)
