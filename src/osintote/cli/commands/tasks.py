# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Task CLI commands — create, list, start, cancel, delete, show."""

from __future__ import annotations

from uuid import UUID

import typer
from sqlmodel import Session, select

from osintote.models.database import get_session
from osintote.models.orm import Log, Target, Task, TaskStatus

app = typer.Typer(help="Task management commands")


def _parse_task_id(task_id: str) -> UUID:
    """Parse and validate a task ID string."""
    try:
        return UUID(task_id)
    except ValueError as exc:
        typer.echo(f"Invalid task ID: {task_id}", err=True)
        raise typer.Exit(code=1) from exc


def _require_task(session: Session, task_id: UUID) -> Task:
    """Get a task or exit with error."""
    task = session.get(Task, task_id)
    if task is None:
        typer.echo(f"Task {task_id} not found.", err=True)
        raise typer.Exit(code=1)
    return task


@app.command("create")
def task_create(
    target_name: str = typer.Argument(..., help="Target name to associate with the task"),
    name: str = typer.Option(..., "-n", "--name", help="Task name"),
    description: str | None = typer.Option(None, "-d", "--description", help="Task description"),
    recipe: str | None = typer.Option(None, "-r", "--recipe", help="Recipe identifier"),
) -> None:
    """Create a new task and add it to the queue."""
    with Session(get_session()) as session:
        target = session.exec(
            select(Target).where(Target.name == target_name)
        ).first()
        if target is None:
            typer.echo(f"Target '{target_name}' not found.", err=True)
            raise typer.Exit(code=1)

        task = Task(
            target_id=target.id,
            name=name,
            description=description,
            recipe=recipe,
            status=TaskStatus.PENDING,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        typer.echo(f"Task created: {task.id}")


@app.command("list")
def task_list(
    target: str | None = typer.Option(None, "-t", "--target", help="Filter by target name"),
    status: str | None = typer.Option(None, "-s", "--status", help="Filter by status"),
    limit: int = typer.Option(50, "-l", "--limit", help="Max results"),
) -> None:
    """List tasks with optional filters."""
    with Session(get_session()) as session:
        query = select(Task)
        if target:
            tgt = session.exec(
                select(Target).where(Target.name == target)
            ).first()
            if tgt:
                query = query.where(Task.target_id == tgt.id)
            else:
                typer.echo(f"Target '{target}' not found.", err=True)
                raise typer.Exit(code=1)
        if status:
            query = query.where(Task.status == status)
        query = query.limit(limit).order_by(Task.created_at.desc())
        tasks = list(session.exec(query).all())  # type: ignore[union-attr]

        if not tasks:
            typer.echo("No tasks found.")
            return

        typer.echo(f"{'ID':<36} {'Name':<25} {'Status':<12} {'Created'}")
        typer.echo("-" * 90)
        for t in tasks:
            typer.echo(f"{t.id!s:<36} {t.name:<25} {t.status.value:<12} {t.created_at}")


@app.command("show")
def task_show(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """Show details of a specific task."""
    uuid_id = _parse_task_id(task_id)
    with Session(get_session()) as session:
        task = _require_task(session, uuid_id)

        typer.echo(f"ID:          {task.id}")
        typer.echo(f"Name:        {task.name}")
        typer.echo(f"Status:      {task.status.value}")
        typer.echo(f"Target ID:   {task.target_id}")
        typer.echo(f"Recipe:      {task.recipe or 'N/A'}")
        typer.echo(f"Progress:    {task.progress}%")
        typer.echo(f"Started:     {task.started_at or 'N/A'}")
        typer.echo(f"Completed:   {task.completed_at or 'N/A'}")
        if task.error_message:
            typer.echo(f"Error:       {task.error_message}")
        if task.description:
            typer.echo(f"Description: {task.description}")


@app.command("start")
def task_start(
    task_id: str = typer.Argument(..., help="Task ID to start"),
) -> None:
    """Start a pending task (transitions to RUNNING).

    NOTE: This updates the DB status directly. The API serve command
    handles actual executor dispatch via the /tasks/{id}/start endpoint.
    """
    uuid_id = _parse_task_id(task_id)
    with Session(get_session()) as session:
        task = _require_task(session, uuid_id)
        if task.status != TaskStatus.PENDING:
            typer.echo(f"Cannot start task in {task.status.value} state.", err=True)
            raise typer.Exit(code=1)

        task.status = TaskStatus.RUNNING
        task.started_at = task.updated_at
        session.add(task)
        session.commit()
        typer.echo(f"Task {task_id} started.")


@app.command("cancel")
def task_cancel(
    task_id: str = typer.Argument(..., help="Task ID to cancel"),
) -> None:
    """Cancel a running or pending task."""
    uuid_id = _parse_task_id(task_id)
    with Session(get_session()) as session:
        task = _require_task(session, uuid_id)
        if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            typer.echo(f"Cannot cancel task in {task.status.value} state.", err=True)
            raise typer.Exit(code=1)

        task.status = TaskStatus.CANCELLED
        task.completed_at = task.updated_at
        session.add(task)
        session.commit()
        typer.echo(f"Task {task_id} cancelled.")


@app.command("delete")
def task_delete(
    task_id: str = typer.Argument(..., help="Task ID to delete"),
    force: bool = typer.Option(False, "-f", "--force", help="Skip confirmation"),
) -> None:
    """Delete a task and its associated errors/logs."""
    uuid_id = _parse_task_id(task_id)
    if not force:
        confirm = typer.confirm(f"Delete task {task_id}?")
        if not confirm:
            raise typer.Exit(code=0)

    with Session(get_session()) as session:
        task = _require_task(session, uuid_id)

        # Clean up related records
        for error in task.errors:  # type: ignore[attr-defined]
            session.delete(error)
        for log in session.exec(select(Log).where(Log.task_id == uuid_id)).all():  # type: ignore[union-attr]
            session.delete(log)

        session.delete(task)
        session.commit()
        typer.echo(f"Task {task_id} deleted.")
