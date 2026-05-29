# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Recon command — rich CLI progress display for task execution.

Subcommands:
    start  — Run a task with live progress bars, colored findings, and summary
    list   — List tasks with status indicators
"""

from __future__ import annotations

import asyncio
import json
import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from sqlmodel import Session, select

from osintote.engine.stage import STAGE_REGISTRY, FakeStage, Stage
from osintote.models.database import get_session
from osintote.models.orm import Target, Task, TaskCreate, TaskStatus
from osintote.recipes import RecipeLoader

logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Recon execution commands")


# ── Live Progress Display ──────────────────────────────────────────────────


class ReconDisplay:
    """Rich terminal display for recon task progress."""

    def __init__(self) -> None:
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        )
        self.stage_tasks: dict[str, int] = {}
        self.findings: list[dict] = []
        self.errors: list[dict] = []
        self.log_lines: list[str] = []

    def start(self) -> None:
        """Start the progress display."""
        self.progress.start()
        console.print()

    def add_stage(self, stage_name: str, total: int = 1) -> str:
        """Add a stage task and return its progress task ID."""
        stage_id = self.progress.add_task(
            description=stage_name,
            total=total,
            visible=True,
        )
        self.stage_tasks[stage_name] = stage_id
        return str(stage_id)

    def update_stage(self, stage_name: str, advance: int = 1, **kwargs) -> None:
        """Advance a stage's progress."""
        if stage_name in self.stage_tasks:
            self.progress.update(
                self.stage_tasks[stage_name],
                advance=advance,
                **kwargs,
            )

    def mark_stage_complete(self, stage_name: str, completed: bool = True) -> None:
        """Mark a stage as completed."""
        if stage_name in self.stage_tasks:
            self.progress.update(
                self.stage_tasks[stage_name],
                completed=completed,
            )

    def add_finding(self, finding: dict) -> None:
        """Add a colored finding to the results."""
        self.findings.append(finding)

    def add_error(self, error: dict) -> None:
        """Add an error entry."""
        self.errors.append(error)

    def add_log(self, message: str) -> None:
        """Add a log line."""
        self.log_lines.append(message)

    def render_summary(self) -> None:
        """Render a summary panel with findings, errors, and stats."""
        console.print()

        # Findings table
        if self.findings:
            findings_table = Table(
                show_header=True,
                header_style="bold cyan",
                border_style="blue",
                title="[bold]Findings[/]",
                pad_edge=True,
            )
            findings_table.add_column("[bold]✓[/]", style="green", justify="center")
            findings_table.add_column("Type", style="cyan")
            findings_table.add_column("Target", style="dim")
            findings_table.add_column("Details", style="white")

            for finding in self.findings:
                icon = "[green]✓[/]" if finding.get("status") != "warning" else "[yellow]![/]"
                findings_table.add_row(
                    icon,
                    finding.get("type", "generic"),
                    finding.get("target", "?"),
                    finding.get("detail", ""),
                )
            console.print(Panel(findings_table, border_style="green"))

        # Errors table
        if self.errors:
            errors_table = Table(
                show_header=True,
                header_style="bold red",
                border_style="red",
                title="[bold]Errors[/]",
                pad_edge=True,
            )
            errors_table.add_column("[bold]✗[/]", style="red", justify="center")
            errors_table.add_column("Stage", style="magenta")
            errors_table.add_column("Message", style="red")

            for err in self.errors:
                errors_table.add_row(
                    "[red]✗[/]",
                    err.get("stage", "unknown"),
                    err.get("message", ""),
                )
            console.print(Panel(errors_table, border_style="red"))

        # Summary stats
        total_stages = len(self.stage_tasks)
        completed_stages = sum(1 for task in self.progress.tasks if task.completed)
        summary_text = (
            f"[bold]Stages:[/]"
            f" [green]{completed_stages}[/] passed / "
            f"[red]{total_stages - completed_stages}[/] failed\n"
            f"[bold]Findings:[/]"
            f" {len(self.findings)}\n"
            f"[bold]Errors:[/]"
            f" {len(self.errors)}"
        )
        if completed_stages == total_stages:
            console.print(
                Panel(
                    summary_text,
                    title="[bold green]Recon Complete[/]",
                    border_style="green",
                )
            )
        elif completed_stages > 0:
            console.print(
                Panel(
                    summary_text,
                    title="[bold yellow]Recon Partial[/]",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel(
                    summary_text,
                    title="[bold red]Recon Failed[/]",
                    border_style="red",
                )
            )

    def render_log(self) -> None:
        """Render scrollable log output."""
        if self.log_lines:
            log_panel = Panel(
                "\n".join(self.log_lines[-50:]),
                title="[bold]Log Output[/]",
                border_style="dim",
                height=15,
            )
            console.print(log_panel)

    def stop(self) -> None:
        """Stop the progress display."""
        self.progress.stop()
        self.render_log()
        self.render_summary()
        console.print()


# ── Commands ─────────────────────────────────────────────────────────────────


@app.command("start")
def recon_start(
    target_name: str = typer.Argument(..., help="Target name to run recon against"),
    recipe: str | None = typer.Option(None, "-r", "--recipe", help="Recipe identifier"),
    name: str = typer.Option("recon", "-n", "--name", help="Task name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without executing"),
) -> None:
    """Run a recon task against a target with rich progress display."""
    display = ReconDisplay()
    display.start()

    try:
        with Session(get_session()) as session:
            target = session.exec(select(Target).where(Target.name == target_name)).first()
            if target is None:
                console.print(f"[red]Target '{target_name}' not found.[/]")
                raise typer.Exit(code=1)

            task_create = TaskCreate(
                target_id=target.id,
                name=name,
                description=f"Recon against {target_name}",
                recipe=recipe,
            )

            task = Task(
                target_id=task_create.target_id,
                name=task_create.name,
                description=task_create.description,
                recipe=task_create.recipe,
                status=TaskStatus.RUNNING,
                started_at=task_create.updated_at,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            stages = _build_stages(recipe)

            if dry_run:
                console.print("[blue]--[/] Dry run mode — no stages executed.")
                task.status = TaskStatus.COMPLETED
                task.completed_at = task.updated_at
                session.add(task)
                session.commit()
                display.render_summary()
                return

            async def _run() -> None:
                for stage in stages:
                    stage_name = stage.name
                    display.add_stage(stage_name)
                    display.add_log(f"[dim]Starting stage:[/dim] {stage_name}")

                    try:
                        result = stage.execute(None)

                        for record in result.records:
                            finding = {
                                "type": stage_name,
                                "target": target_name,
                                "detail": json.dumps(record)[:80],
                                "status": "ok",
                            }
                            display.add_finding(finding)
                            display.update_stage(stage_name, advance=1)

                        display.mark_stage_complete(stage_name, completed=True)
                        display.add_log(f"[green]Stage {stage_name} completed[/]")

                    except Exception as exc:
                        display.mark_stage_complete(stage_name, completed=False)
                        display.add_error({"stage": stage_name, "message": str(exc)})
                        display.add_log(f"[red]Stage {stage_name} failed: {exc}[/]")

                console.print()
                task.status = TaskStatus.COMPLETED
                task.completed_at = task.updated_at
                session.add(task)
                session.commit()

            asyncio.run(_run())

    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
        raise typer.Exit(code=1) from exc
    finally:
        display.stop()


@app.command("list")
def recon_list(
    target: str | None = typer.Option(None, "-t", "--target", help="Filter by target"),
    status: str | None = typer.Option(None, "-s", "--status", help="Filter by status"),
) -> None:
    """List recon tasks with status indicators."""
    with Session(get_session()) as session:
        query = select(Task)
        if target:
            tgt = session.exec(select(Target).where(Target.name == target)).first()
            if tgt:
                query = query.where(Task.target_id == tgt.id)
            else:
                console.print(f"[red]Target '{target}' not found.[/]")
                raise typer.Exit(code=1)
        if status:
            query = query.where(Task.status == status)
        tasks = list(session.exec(query.order_by(Task.created_at.desc())).all())

    if not tasks:
        console.print("[blue]--[/] No tasks found.")
        return

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
    )
    table.add_column("[bold]ID[/]", style="dim", width=9)
    table.add_column("[bold]Name[/]")
    table.add_column("[bold]Status[/]", style="green")
    table.add_column("[bold]Progress[/]")
    table.add_column("[bold]Created[/]")

    status_icons = {
        TaskStatus.PENDING: "[blue]○[/]",
        TaskStatus.RUNNING: "[yellow]▶[/]",
        TaskStatus.COMPLETED: "[green]✓[/]",
        TaskStatus.FAILED: "[red]✗[/]",
        TaskStatus.CANCELLED: "[dim]—[/]",
        TaskStatus.PAUSED: "[yellow]||[/]",
    }

    for t in tasks:
        icon = status_icons.get(t.status, "[dim]?[/]")
        table.add_row(
            str(t.id)[:8],
            t.name,
            f"{icon} {t.status.value}",
            f"{t.progress}%",
            t.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def _build_stages(recipe: str | None) -> list[Stage]:
    """Build stages from recipe or use defaults."""
    if recipe:
        return _load_recipe_stages(recipe)

    return [FakeStage(success=True, data={}, records_count=0)]


def _load_recipe_stages(recipe_name: str) -> list[Stage]:
    """Load stages from a recipe definition."""
    loader = RecipeLoader()
    recipe = loader.get_recipe(recipe_name)
    if recipe is None:
        console.print(f"[yellow]Recipe '{recipe_name}' not found, using defaults[/]")
        return [FakeStage(success=True, data={}, records_count=0)]

    stages: list[Stage] = []
    for stage_def in recipe.ordered_stages():
        stage_cls = STAGE_REGISTRY.get(stage_def.stage)
        if stage_cls is None:
            console.print(f"[yellow]Unknown stage '{stage_def.stage}', skipping[/]")
            continue
        stages.append(stage_cls(**(stage_def.params or {})))

    if not stages:
        return [FakeStage(success=True, data={}, records_count=0)]
    return stages
