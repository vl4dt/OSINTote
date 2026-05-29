# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the Executor engine."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from osintote.engine.executor import ExecutionEvent, Executor
from osintote.engine.stage import FakeStage, Stage, StageContext, StageResult


# ── ExecutionEvent ──────────────────────────────────────────────────────────


class TestExecutionEvent:
    """Tests for ExecutionEvent dataclass."""

    def test_to_dict_minimal(self) -> None:
        event = ExecutionEvent(task_id="t1", event_type="task_started")
        assert event.to_dict() == {
            "task_id": "t1",
            "event": "task_started",
        }

    def test_to_dict_full(self) -> None:
        event = ExecutionEvent(
            task_id="t1",
            event_type="stage_complete",
            stage_name="dns",
            data={"success": True, "records_count": 5},
        )
        expected = {
            "task_id": "t1",
            "event": "stage_complete",
            "stage": "dns",
            "data": {"success": True, "records_count": 5},
        }
        assert event.to_dict() == expected

    def test_format_sse(self) -> None:
        event = ExecutionEvent(task_id="t1", event_type="task_started")
        sse = event.format_sse()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")

    def test_to_json(self) -> None:
        event = ExecutionEvent(task_id="t1", event_type="task_started")
        json_str = event.to_json()
        assert '"task_id"' in json_str
        assert '"event"' in json_str


# ── Executor lifecycle ─────────────────────────────────────────────────────


class TestExecutorLifecycle:
    """Tests for Executor start/stop."""

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        executor = Executor(max_concurrent=2, cpu_workers=2)
        await executor.start()
        assert executor._running is True
        assert len(executor._workers) == 2
        await executor.stop()
        assert executor._running is False

    @pytest.mark.asyncio
    async def test_status(self) -> None:
        executor = Executor(max_concurrent=4, cpu_workers=4)
        await executor.start()
        status = executor.get_status()
        assert status["running"] is True
        assert status["max_concurrent"] == 4
        assert len(status["workers"]) == 4
        assert status["queue_size"] == 0
        await executor.stop()


# ── Event system ───────────────────────────────────────────────────────────


class TestExecutorEvents:
    """Tests for executor event handling."""

    @pytest.mark.asyncio
    async def test_on_event_handler(self) -> None:
        executor = Executor()
        received: list[ExecutionEvent] = []
        executor.on_event(received.append)

        await executor.start()
        event = ExecutionEvent(task_id="t1", event_type="test")
        executor._emit(event)
        assert len(received) == 1
        assert received[0].task_id == "t1"
        await executor.stop()

    @pytest.mark.asyncio
    async def test_get_events_filtered(self) -> None:
        executor = Executor()
        await executor.start()
        executor._emit(ExecutionEvent(task_id="t1", event_type="a"))
        executor._emit(ExecutionEvent(task_id="t2", event_type="b"))
        executor._emit(ExecutionEvent(task_id="t1", event_type="c"))

        t1_events = executor.get_events("t1")
        assert len(t1_events) == 2
        t2_events = executor.get_events("t2")
        assert len(t2_events) == 1
        all_events = executor.get_events()
        assert len(all_events) == 3
        await executor.stop()

    @pytest.mark.asyncio
    async def test_clear_events(self) -> None:
        executor = Executor()
        await executor.start()
        executor._emit(ExecutionEvent(task_id="t1", event_type="a"))
        executor.clear_events()
        assert len(executor.get_events()) == 0
        await executor.stop()


# ── Task execution ─────────────────────────────────────────────────────────


class TestExecutorExecution:
    """Tests for task submission and execution."""

    @pytest.mark.asyncio
    async def test_submit_and_run_light_stages(self) -> None:
        """Executor should run light stages concurrently."""
        executor = Executor(max_concurrent=4, cpu_workers=2)
        await executor.start()

        stage = FakeStage(success=True, data={"ip": "1.2.3.4"}, records_count=1)
        executor._semaphore = asyncio.Semaphore(4)  # Set up semaphore manually

        from osintote.engine.executor import TaskItem
        item = TaskItem(
            task_id="t1",
            target_name="test.com",
            stages=[stage],
            priority=1,
            event_callback=executor._on_task_event,
        )
        results = await executor._execute_task(item)
        assert len(results) == 1
        assert results[0].success is True
        await executor.stop()

    @pytest.mark.asyncio
    async def test_submit_method(self) -> None:
        executor = Executor()
        await executor.start()

        stage = FakeStage(success=True)
        task_id = await executor.submit(
            task_id="t1",
            target_name="test.com",
            stages=[stage],
            priority=1,
        )
        assert task_id == "t1"
        assert executor._task_queue.qsize() == 1
        await executor.stop()

    @pytest.mark.asyncio
    async def test_cancel_task(self) -> None:
        executor = Executor()
        await executor.start()
        executor.cancel("t1")
        assert executor.is_cancelled("t1") is True
        assert executor.is_cancelled("t2") is False
        await executor.stop()

    @pytest.mark.asyncio
    async def test_task_results(self) -> None:
        executor = Executor()
        executor._tasks_done["t1"] = [
            StageResult(success=True, data={"found": True}),
        ]
        results = executor.get_task_results("t1")
        assert results is not None
        assert len(results) == 1
        assert executor.get_task_results("nonexistent") is None

    @pytest.mark.asyncio
    async def test_multiple_event_handlers(self) -> None:
        """Multiple event handlers should all receive events."""
        executor = Executor()
        received_a: list[ExecutionEvent] = []
        received_b: list[ExecutionEvent] = []
        executor.on_event(received_a.append)
        executor.on_event(received_b.append)

        await executor.start()
        executor._emit(ExecutionEvent(task_id="t1", event_type="test"))
        assert len(received_a) == 1
        assert len(received_b) == 1
        await executor.stop()


# ── Worker management ──────────────────────────────────────────────────────


class TestWorkerManagement:
    """Tests for worker lifecycle."""

    @pytest.mark.asyncio
    async def test_worker_info(self) -> None:
        from osintote.engine.executor import WorkerInfo

        w = WorkerInfo()
        assert w.status == "idle"
        assert w.tasks_completed == 0
        assert w.tasks_failed == 0
        assert w.active_task_id is None


# ── Integration: Executor + Stages ─────────────────────────────────────────


class TestExecutorIntegration:
    """Integration tests for Executor with real stages."""

    @pytest.mark.asyncio
    async def test_executor_run_with_fake_stages(self) -> None:
        """Full integration: submit task, let workers process it."""
        executor = Executor(max_concurrent=4, cpu_workers=2)
        await executor.start()

        events: list[ExecutionEvent] = []
        executor.on_event(events.append)

        stage_a = FakeStage(success=True, data={"a": 1}, records_count=1, message="A done")
        stage_b = FakeStage(success=True, data={"b": 2}, records_count=2, message="B done")

        task_id = await executor.submit(
            task_id="t1",
            target_name="test.com",
            stages=[stage_a, stage_b],
            priority=1,
        )

        # Wait for worker to process
        await asyncio.sleep(0.2)

        results = executor.get_task_results(task_id)
        assert results is not None
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

        # Events should include task_started and stage_complete events
        task_events = [e for e in events if e.task_id == task_id]
        event_types = [e.event_type for e in task_events]
        assert "task_started" in event_types
        assert "stage_complete" in event_types
        assert "task_finished" in event_types

        await executor.stop()

    @pytest.mark.asyncio
    async def test_executor_cancel_during_execution(self) -> None:
        """Executor should respect cancellation requests."""
        executor = Executor(max_concurrent=4, cpu_workers=2)
        await executor.start()

        # Create a slow stage
        slow_stage = FakeStage(execute_delay=5.0)
        executor._semaphore = asyncio.Semaphore(4)

        from osintote.engine.executor import TaskItem
        item = TaskItem(
            task_id="t1",
            target_name="test.com",
            stages=[slow_stage],
            priority=1,
            event_callback=executor._on_task_event,
        )

        executor.cancel("t1")
        results = await executor._execute_task(item)
        # Cancellation before any stages run → 0 results, status=cancelled
        assert len(results) == 0
        await executor.stop()

    @pytest.mark.asyncio
    async def test_executor_with_failing_stages(self) -> None:
        """Executor should handle stage failures gracefully."""
        executor = Executor()
        await executor.start()

        good = FakeStage(success=True, data={"good": True})
        bad = FakeStage(success=False, error="BOOM")

        executor._semaphore = asyncio.Semaphore(4)

        from osintote.engine.executor import TaskItem
        item = TaskItem(
            task_id="t1",
            target_name="test.com",
            stages=[good, bad],
            priority=1,
            event_callback=executor._on_task_event,
        )

        results = await executor._execute_task(item)
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        await executor.stop()
