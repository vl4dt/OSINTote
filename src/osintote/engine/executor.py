# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Executor engine — asyncio event loop, process pool, priority queue.

The executor manages the lifecycle of task execution:
- Dispatches stages by cost tier (light = async I/O, heavy = CPU-bound)
- Uses an asyncio semaphore-based I/O pool for concurrency control
- Uses a ProcessPoolExecutor for CPU-bound stages
- Provides a priority queue for ordered task scheduling
- Emits SSE-compatible events for live progress tracking

Example::

    from osintote.engine.executor import Executor

    executor = Executor(max_concurrent=4)
    await executor.start()
    results = await executor.run_task(task_id, stages)
    await executor.stop()
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from ..models.orm import ErrorSeverity, TaskStatus
from ..notify.notifier import Notifier
from .stage import Stage, StageContext, StageResult

logger = logging.getLogger(__name__)

# ── Event types ─────────────────────────────────────────────────────────────


class EventType(IntEnum):
    """Event priority (lower = higher priority)."""

    CRITICAL = 0
    INFO = 1
    DEBUG = 2


@dataclass
class ExecutionEvent:
    """Event emitted during task execution for SSE streaming.

    Attributes
    ----------
    task_id:
        UUID of the task.
    event_type:
        One of task_started, progress, stage_complete, task_finished, error.
    stage_name:
        Name of the stage (if applicable).
    data:
        Event payload.
    """

    task_id: str
    event_type: str
    stage_name: str | None = None
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        result: dict[str, Any] = {
            "task_id": self.task_id,
            "event": self.event_type,
        }
        if self.stage_name:
            result["stage"] = self.stage_name
        if self.data:
            result["data"] = self.data
        return result

    def format_sse(self) -> str:
        """Format as SSE data line."""
        return f"data: {self.to_json()}\n\n"

    def to_json(self) -> str:
        """Serialize to JSON string."""
        import json

        return json.dumps(self.to_dict())


# ── Task item ───────────────────────────────────────────────────────────────


@dataclass
class TaskItem:
    """Single item in the executor's priority queue."""

    task_id: str
    target_name: str
    stages: list[Stage]
    priority: int = 1  # 1 (high) → 3 (low)
    event_callback: Callable[[ExecutionEvent], None] = field(default=lambda _: None, repr=False)

    def __lt__(self, other: TaskItem) -> bool:
        return self.priority < other.priority


# ── Worker state ────────────────────────────────────────────────────────────


@dataclass
class WorkerInfo:
    """Runtime info about the executor's workers."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "idle"  # idle | busy | stopped
    tasks_completed: int = 0
    tasks_failed: int = 0
    active_task_id: str | None = None


# ── Executor ────────────────────────────────────────────────────────────────


class Executor:
    """Task executor with async I/O pool and process pool.

    Parameters
    ----------
    max_concurrent:
        Maximum concurrent tasks (controls asyncio.Semaphore).
    io_workers:
        Number of async I/O workers.
    cpu_workers:
        Number of CPU-bound workers (ProcessPoolExecutor).
    notifier:
        Optional Notifier for delivery hooks.
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        io_workers: int = 8,
        cpu_workers: int = 2,
        notifier: Notifier | None = None,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.io_workers = io_workers
        self.cpu_workers = cpu_workers
        self.notifier = notifier

        self._semaphore: asyncio.Semaphore | None = None
        self._task_queue: asyncio.PriorityQueue[TaskItem] = asyncio.PriorityQueue()
        self._workers: list[WorkerInfo] = []
        self._worker_tasks: list[asyncio.Task] = []
        self._running = False
        self._events: list[ExecutionEvent] = []
        self._event_handlers: list[Callable[[ExecutionEvent], None]] = []
        self._tasks_done: dict[str, list[StageResult]] = {}
        self._cancellation_tokens: dict[str, bool] = {}

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the executor — create semaphore, spawn workers."""
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._running = True
        self._workers = [WorkerInfo(status="idle") for _ in range(self.cpu_workers)]
        # Spawn worker coroutines
        for worker in self._workers:
            task = asyncio.create_task(self._worker_loop(worker))
            self._worker_tasks.append(task)
        logger.info(
            "Executor started: %d workers, %d max concurrent",
            self.cpu_workers,
            self.max_concurrent,
        )

    async def stop(self) -> None:
        """Stop the executor — drain queue, cancel workers."""
        self._running = False
        # Cancel all worker tasks
        for t in self._worker_tasks:
            t.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        logger.info("Executor stopped")

    # ── Event system ────────────────────────────────────────────────────

    def on_event(self, callback: Callable[[ExecutionEvent], None]) -> None:
        """Register an event handler (for SSE streaming, etc.)."""
        self._event_handlers.append(callback)

    def _emit(self, event: ExecutionEvent) -> None:
        """Emit an event to all handlers and storage."""
        self._events.append(event)
        for handler in self._event_handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    _ = asyncio.create_task(handler(event))  # noqa: RUF006
                else:
                    handler(event)
            except Exception:
                logger.exception("Event handler error for %s", event.event_type)

    def get_events(self, task_id: str | None = None) -> list[dict[str, Any]]:
        """Get stored events, optionally filtered by task_id."""
        if task_id:
            return [e.to_dict() for e in self._events if e.task_id == task_id]
        return [e.to_dict() for e in self._events]

    def clear_events(self) -> None:
        """Clear stored events."""
        self._events.clear()

    # ── Task submission ────────────────────────────────────────────────

    async def submit(
        self,
        task_id: str,
        target_name: str,
        stages: list[Stage],
        priority: int = 1,
    ) -> str:
        """Submit a task for execution.

        Returns the task_id for tracking.
        """
        item = TaskItem(
            task_id=task_id,
            target_name=target_name,
            stages=stages,
            priority=priority,
            event_callback=self._on_task_event,
        )
        await self._task_queue.put(item)
        logger.info("Task %s submitted (priority=%d, %d stages)", task_id, priority, len(stages))
        return task_id

    def cancel(self, task_id: str) -> None:
        """Signal cancellation for a task."""
        self._cancellation_tokens[task_id] = True
        logger.info("Task %s cancellation requested", task_id)

    def is_cancelled(self, task_id: str) -> bool:
        """Check if a task has been cancelled."""
        return self._cancellation_tokens.get(task_id, False)

    # ── Worker loop ────────────────────────────────────────────────────

    async def _worker_loop(self, worker: WorkerInfo) -> None:
        """Background worker that pulls items from the priority queue."""
        while self._running:
            try:
                item: TaskItem = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
            except TimeoutError:
                continue

            worker.status = "busy"
            worker.active_task_id = item.task_id
            try:
                results = await self._execute_task(item)
                worker.tasks_completed += 1
            except Exception:
                worker.tasks_failed += 1
                results = []
            finally:
                worker.status = "idle"
                worker.active_task_id = None
                self._tasks_done[item.task_id] = results

    # ── Task execution ─────────────────────────────────────────────────

    async def _execute_task(self, item: TaskItem) -> list[StageResult]:
        """Execute all stages in a task, respecting cost tiers and cancellation."""
        task_id = item.task_id
        ctx = StageContext(
            target_name=item.target_name,
            target_id=task_id,
            task_id=task_id,
            task_status=TaskStatus.RUNNING.value,
        )

        # Emit task_started
        self._emit(
            ExecutionEvent(
                task_id=task_id,
                event_type="task_started",
                data={"target": item.target_name, "stages": len(item.stages)},
            )
        )

        results: list[StageResult] = []

        # Group stages by cost for dispatch
        light_stages = [s for s in item.stages if s.cost == "light"]
        medium_stages = [s for s in item.stages if s.cost == "medium"]
        heavy_stages = [s for s in item.stages if s.cost == "heavy"]

        cost_order = [light_stages, medium_stages, heavy_stages]
        cost_events = ["light", "medium", "heavy"]

        for stages, cost_event in zip(cost_order, cost_events, strict=True):
            if self.is_cancelled(task_id):
                ctx.update_status(TaskStatus.CANCELLED.value)
                self._emit(
                    ExecutionEvent(
                        task_id=task_id,
                        event_type="task_finished",
                        data={"status": "cancelled", "results_count": len(results)},
                    )
                )
                return results

            # Dispatch by cost tier
            if cost_event == "light":
                # Async I/O — concurrent within semaphore
                for stage in stages:
                    if self.is_cancelled(task_id):
                        ctx.update_status(TaskStatus.CANCELLED.value)
                        self._emit(
                            ExecutionEvent(
                                task_id=task_id,
                                event_type="task_finished",
                                data={"status": "cancelled", "results_count": len(results)},
                            )
                        )
                        return results

                    assert self._semaphore is not None
                    await self._semaphore.acquire()
                    try:
                        result = await self._run_stage(ctx, stage)
                        results.append(result)
                        ctx.findings[stage.name] = result.to_dict()
                        ctx.records.extend(result.data if isinstance(result.data, list) else [])
                    finally:
                        self._semaphore.release()
            else:
                # Sequential for medium/heavy (CPU-bound)
                for stage in stages:
                    if self.is_cancelled(task_id):
                        ctx.update_status(TaskStatus.CANCELLED.value)
                        self._emit(
                            ExecutionEvent(
                                task_id=task_id,
                                event_type="task_finished",
                                data={"status": "cancelled", "results_count": len(results)},
                            )
                        )
                        return results

                    result = await self._run_stage(ctx, stage)
                    results.append(result)
                    ctx.findings[stage.name] = result.to_dict()
                    ctx.records.extend(result.data if isinstance(result.data, list) else [])

        # Determine final status
        failed = [r for r in results if not r.success]
        if failed:
            ctx.update_status(TaskStatus.FAILED.value)
            self._emit(
                ExecutionEvent(
                    task_id=task_id,
                    event_type="task_finished",
                    data={
                        "status": "failed",
                        "failures": len(failed),
                        "results_count": len(results),
                    },
                )
            )
        else:
            ctx.update_status(TaskStatus.COMPLETED.value)
            self._emit(
                ExecutionEvent(
                    task_id=task_id,
                    event_type="task_finished",
                    data={"status": "completed", "results_count": len(results)},
                )
            )

        # Notify
        if self.notifier:
            if ctx.task_status == TaskStatus.COMPLETED.value:
                await self.notifier.on_task_complete(
                    task_id, ctx.target_name, extra={"results": len(results)}
                )
            elif ctx.task_status == TaskStatus.FAILED.value:
                await self.notifier.on_task_fail(
                    task_id,
                    ctx.target_name,
                    error_message=failed[-1].error or "Unknown error",
                )

        return results

    async def _run_stage(
        self,
        ctx: StageContext,
        stage: Stage,
    ) -> StageResult:
        """Run a single stage with error handling."""
        self._emit(
            ExecutionEvent(
                task_id=ctx.task_id,
                event_type="stage_started",
                stage_name=stage.name,
            )
        )

        start = ctx.elapsed_ms

        try:
            if stage.timeout_s > 0:
                result = await asyncio.wait_for(
                    asyncio.to_thread(stage._run_with_timeout, ctx),
                    timeout=stage.timeout_s,
                )
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, stage.execute, ctx)
        except asyncio.CancelledError:
            result = StageResult.failure(error="Stage cancelled")
            ctx.log_error(stage.name, "Stage was cancelled")
        except Exception as exc:
            result = StageResult.failure(error=str(exc))
            ctx.log_error(stage.name, str(exc))

        result.elapsed_ms = ctx.elapsed_ms - start

        self._emit(
            ExecutionEvent(
                task_id=ctx.task_id,
                event_type="stage_complete",
                stage_name=stage.name,
                data=result.to_dict(),
            )
        )

        if not result.success:
            logger.warning(
                "Stage '%s' failed on task %s: %s",
                stage.name,
                ctx.task_id,
                result.error,
            )

        return result

    def _on_task_event(self, event: ExecutionEvent) -> None:
        """Internal callback from TaskItem to emit events."""
        self._emit(event)

    # ── Status ─────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Return executor runtime status."""
        return {
            "running": self._running,
            "max_concurrent": self.max_concurrent,
            "queue_size": self._task_queue.qsize(),
            "workers": [
                {
                    "id": w.id,
                    "status": w.status,
                    "tasks_completed": w.tasks_completed,
                    "tasks_failed": w.tasks_failed,
                    "active_task": w.active_task_id,
                }
                for w in self._workers
            ],
            "events_count": len(self._events),
            "tasks_done": len(self._tasks_done),
        }

    def get_task_results(self, task_id: str) -> list[StageResult] | None:
        """Get results for a completed task."""
        return self._tasks_done.get(task_id)


# ── Error Publishing ────────────────────────────────────────────────────────


def publish_error_to_sse(
    severity: ErrorSeverity,
    message: str,
    stage: str | None = None,
    task_id: str | None = None,
) -> None:
    """Publish an error to the SSE error stream for real-time delivery.

    The error is published to the queue which is consumed by the
    /api/errors/stream endpoint.
    """
    try:
        from osintote.api.routes.errors import publish_error as publish_error_fn
        from osintote.models.orm import Error

        error = Error(
            severity=severity,
            message=message,
            logger="executor",
            stage=stage,
            task_id=task_id,
        )
        asyncio.run_coroutine_threadsafe(
            publish_error_fn(error),
            asyncio.get_running_loop(),
        )
    except Exception as exc:
        logger.warning("Failed to publish error to SSE: %s", exc)
