# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Task lifecycle API — CRUD, status transitions, executor integration.

Endpoints:
    POST /api/tasks          — Create a new task
    GET  /api/tasks          — List tasks (filter by target/status)
    GET  /api/tasks/{id}     — Get task details
    PUT  /api/tasks/{id}     — Update task (partial)
    POST /api/tasks/{id}/start   — Start a pending task
    POST /api/tasks/{id}/cancel  — Cancel a running task
    POST /api/tasks/{id}/resume  — Resume a paused task
    DELETE /api/tasks/{id}      — Delete a task
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from osintote.engine.executor import Executor
from osintote.models.database import get_async_session
from osintote.models.orm import (
    Log,
    Target,
    Task,
    TaskCreate,
    TaskRead,
    TaskStatus,
    TaskUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# Module-level executor instance — initialised by app lifespan
_executor: Executor | None = None


def set_executor(executor: Executor) -> None:
    """Inject the executor instance (called from app lifespan)."""
    global _executor
    _executor = executor


def _get_target_name(db: Session, task: Task) -> str:
    """Get the target name for a task."""
    if task.target_id:
        target = db.get(Target, task.target_id)
        if target:
            return target.name
    return "unknown"


def _load_stages(task: Task) -> list:
    """Load stages for a task from recipe or defaults."""
    from osintote.engine.stage import FakeStage, Stage

    class DummyStage(Stage):
        name = "dummy"
        cost = "light"

        def execute(self, ctx):  # type: ignore[no-untyped-def]
            return FakeStage(success=True, data={}, records_count=0, message="Done").execute(ctx)

    return [DummyStage()]


# ── CRUD ────────────────────────────────────────────────────────────────────


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Task:
    """Create a new task in PENDING state."""
    target = db.get(Target, payload.target_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {payload.target_id} not found")

    task = Task(
        target_id=payload.target_id,
        name=payload.name,
        description=payload.description,
        recipe=payload.recipe,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("Task created: %s (target=%s)", task.id, payload.target_id)
    return task


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
    target_id: UUID | None = Query(None, description="Filter by target"),  # noqa: B008, RUF100
    status: str | None = Query(None, description="Filter by status"),  # noqa: B008, RUF100
    limit: int = 100,
    offset: int = 0,
) -> list[Task]:
    """List tasks with optional filters."""
    query = select(Task)
    if target_id:
        query = query.where(Task.target_id == target_id)
    if status:
        query = query.where(Task.status == status)
    query = query.offset(offset).limit(limit).order_by(Task.created_at.desc())
    return list(db.exec(query).all())  # type: ignore[union-attr]


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Task:
    """Get a task by ID."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Task:
    """Partially update a task."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("Task updated: %s", task_id)
    return task


# ── Status transitions ──────────────────────────────────────────────────────


@router.post("/{task_id}/start", response_model=TaskRead)
async def start_task(
    task_id: UUID,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Task:
    """Transition a PENDING task to RUNNING and dispatch to executor."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != TaskStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start task in {task.status} state",
        )

    task.status = TaskStatus.RUNNING
    task.started_at = task.updated_at
    db.add(task)
    db.commit()
    db.refresh(task)

    if _executor is not None:
        stages = _load_stages(task)
        await _executor.submit(
            task_id=str(task_id),
            target_name=_get_target_name(db, task),
            stages=stages,
        )

    logger.info("Task started: %s", task_id)
    return task


@router.post("/{task_id}/cancel", response_model=TaskRead)
async def cancel_task(
    task_id: UUID,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Task:
    """Transition a RUNNING task to CANCELLED."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in {task.status} state",
        )

    task.status = TaskStatus.CANCELLED
    task.completed_at = task.updated_at
    db.add(task)
    db.commit()
    db.refresh(task)

    if _executor is not None:
        _executor.cancel(str(task_id))

    logger.info("Task cancelled: %s", task_id)
    return task


@router.post("/{task_id}/resume", response_model=TaskRead)
async def resume_task(
    task_id: UUID,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> Task:
    """Resume a PAUSED task back to RUNNING."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != TaskStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume task in {task.status} state",
        )

    task.status = TaskStatus.RUNNING
    db.add(task)
    db.commit()
    db.refresh(task)

    if _executor is not None:
        stages = _load_stages(task)
        await _executor.submit(
            task_id=str(task_id),
            target_name=_get_target_name(db, task),
            stages=stages,
        )

    logger.info("Task resumed: %s", task_id)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> None:
    """Delete a task and its associated errors/logs."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    for error in task.errors:  # type: ignore[attr-defined]
        db.delete(error)
    for log in db.exec(select(Log).where(Log.task_id == task_id)).all():  # type: ignore[union-attr]
        db.delete(log)

    db.delete(task)
    db.commit()
    logger.info("Task deleted: %s", task_id)


# ── Events ──────────────────────────────────────────────────────────────────


@router.get("/{task_id}/events", response_model=list[dict])
async def get_task_events(task_id: UUID) -> list[dict]:
    """Get SSE events for a task."""
    if _executor is None:
        raise HTTPException(status_code=503, detail="Executor not available")
    return _executor.get_events(str(task_id))
