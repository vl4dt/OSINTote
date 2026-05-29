# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Recon command — rich CLI progress display for task execution.

Subcommands:
    start  — Run a task with live progress bars, colored findings, and summary
    list   — List tasks with status indicators

Features:
    - Live progress bars per stage with spinner animation
    - Colored findings (✓/!/✗) with type, target, and details
    - Scrollable log panel showing last N entries
    - Summary panel with stage stats, findings count, and error count
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
)
from rich.rule import Rule
from rich.table import Table
from sqlmodel import Session, select

from osintote.engine.executor import ExecutionEvent, Executor
from osintote.engine.stage import STAGE_REGISTRY, FakeStage, Stage
from osintote.models.database import get_session
from osintote.models.orm import Target, Task, TaskCreate, TaskStatus
from osintote.recipes import RecipeLoader

logger = logging.getLogger(__name__)
console = Console()

app = typer.Typer(help="Recon execution commands")


# ── Stage State ─────────────────────────────────────────────────────────────


@dataclass
class StageState:
    """Per-stage execution state for display."""

    name: str
    total: int = 0
    completed: int = 0
    success: bool = False
    error: str | None = None
    elapsed_ms: float = 0.0
    records: list[dict[str, Any]] = field(default_factory=list)


# ── Live Progress Display ───────────────────────────────────────────────────


class ReconDisplay:
    """Rich terminal display for recon task progress.

    Renders:
        - Stage progress bars with per-stage spinners
        - Findings table (✓/!/✗ icons by severity)
        - Error table with stage and message
        - Scrollable log panel (last 50 lines)
        - Summary panel with stats
    """

    def __init__(self) -> None:
        self.stages: dict[str, StageState] = {}
        self.findings: list[dict[str, str]] = []
        self.errors: list[dict[str, str]] = []
        self.log_lines: list[str] = []
        self._start_time: float = time.time()
        self._progress: Progress | None = None
        self._stage_task_ids: dict[str, int] = {}

    @property
    def elapsed_seconds(self) -> float:
        """Total elapsed time in seconds."""
        return time.time() - self._start_time

    # ── Stage management ───────────────────────────────────────────────

    def add_stage(self, stage_name: str, total: int = 1) -> None:
        """Register a new stage for tracking."""
        self.stages[stage_name] = StageState(name=stage_name, total=total)

    def update_stage(
        self, stage_name: str, completed: int = 0, success: bool = True, elapsed_ms: float = 0.0
    ) -> None:
        """Update a stage's progress state."""
        if stage_name in self.stages:
            stage = self.stages[stage_name]
            stage.completed = completed
            stage.success = success
            stage.elapsed_ms = elapsed_ms

    def complete_stage(
        self, stage_name: str, success: bool = True, elapsed_ms: float = 0.0
    ) -> None:
        """Mark a stage as completed (total = completed)."""
        if stage_name in self.stages:
            self.update_stage(
                stage_name,
                completed=self.stages[stage_name].total,
                success=success,
                elapsed_ms=elapsed_ms,
            )

    def fail_stage(self, stage_name: str, error: str) -> None:
        """Mark a stage as failed."""
        if stage_name in self.stages:
            self.stages[stage_name].success = False
            self.stages[stage_name].error = error

    # ── Findings and errors ────────────────────────────────────────────

    def add_finding(self, finding: dict[str, str]) -> None:
        """Add a colored finding. Status: ok→✓, warning→!, error→✗."""
        self.findings.append(finding)

    def add_error(self, stage: str, message: str) -> None:
        """Add an error entry."""
        self.errors.append({"stage": stage, "message": message})

    def add_log(self, message: str) -> None:
        """Add a log line."""
        self.log_lines.append(message)

    # ── Event handling ─────────────────────────────────────────────────

    def on_event(self, event: ExecutionEvent) -> None:
        """Handle an ExecutionEvent from the Executor."""
        etype = event.event_type
        stage = event.stage_name or ""

        if etype == "task_started":
            data = event.data or {}
            self.add_log(f"  [bold blue]▶[/] Task started: {data.get('target', '?')}")
            self.add_log(f"  [dim]Stages:[/dim] {data.get('stages', '?')}")

        elif etype == "stage_started":
            self.add_log(f"  [dim]  → {stage}[/]")

        elif etype == "stage_complete":
            data = event.data or {}
            elapsed = data.get("elapsed_ms", 0)
            success = data.get("success", False)
            self.complete_stage(stage, success=success, elapsed_ms=elapsed)
            icon = "[green]✓[/]" if success else "[red]✗[/]"
            msg = data.get("message", "")
            self.add_log(f"  {icon} [dim]{stage}[/] — {msg} ({elapsed:.0f}ms)")

        elif etype == "task_finished":
            data = event.data or {}
            status = data.get("status", "unknown")
            results_count = data.get("results_count", 0)
            self.add_log(f"\n  [bold]Task finished:[/bold] {status}")
            self.add_log(f"  [dim]Results:[/dim] {results_count}")

    # ── Rendering ──────────────────────────────────────────────────────

    def _render_stage_table(self) -> Table:
        """Render stage progress table with spinners and progress bars."""
        table = Table(
            show_header=False,
            box=None,
            pad_edge=True,
            padding=(0, 1),
        )
        table.add_column("icon", width=3, justify="center")
        table.add_column("stage", style="cyan", no_wrap=True)
        table.add_column("progress", width=30)
        table.add_column("stats", style="dim", width=18, justify="right")

        for name, state in self.stages.items():
            if not state.success and state.error:
                icon = "[red]✗[/]"
            elif state.success and state.total > 0:
                icon = "[green]✓[/]"
            elif state.completed < state.total:
                icon = "[yellow]⟳[/]"
            else:
                icon = "[dim]○[/]"

            # Build progress bar text
            if state.total > 0:
                pct = (state.completed / state.total) * 100
                bar_text = f"[bold blue]{state.completed}/{state.total}[/] ({pct:.0f}%)"
            else:
                bar_text = f"[bold blue]{state.completed}/?[/]"

            # Elapsed time
            stats_text = f"{state.elapsed_ms / 1000:.1f}s" if state.elapsed_ms > 0 else "—"

            table.add_row(icon, name, bar_text, stats_text)

        return table

    def _render_findings_table(self) -> Table:
        """Render colored findings table (✓/!/✗)."""
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            title="[bold]Findings[/]",
            pad_edge=True,
            title_justify="left",
            title_style="bold green",
        )
        table.add_column("status", style="green", justify="center", width=3)
        table.add_column("type", style="cyan")
        table.add_column("target", style="dim")
        table.add_column("detail", style="white")

        for f in self.findings:
            status = f.get("status", "ok")
            if status == "warning":
                icon = "[yellow]![/]"
            elif status in ("error", "critical"):
                icon = "[red]✗[/]"
            else:
                icon = "[green]✓[/]"

            table.add_row(
                icon,
                f.get("type", ""),
                f.get("target", ""),
                f.get("detail", ""),
            )

        return table

    def _render_errors_panel(self) -> Panel | None:
        """Render errors panel."""
        if not self.errors:
            return None

        table = Table(
            show_header=True,
            header_style="bold red",
            border_style="red",
            title="[bold]Errors[/]",
            pad_edge=True,
            title_justify="left",
        )
        table.add_column("✗", style="red", justify="center", width=3)
        table.add_column("stage", style="magenta")
        table.add_column("message", style="red")

        for e in self.errors:
            table.add_row("[red]✗[/]", e.get("stage", "?"), e.get("message", ""))

        return Panel(table, border_style="red")

    def _render_log_panel(self) -> Panel:
        """Render scrollable log panel (last 50 lines)."""
        recent = self.log_lines[-50:] if self.log_lines else ["  (no log output yet)"]
        return Panel(
            "\n".join(recent),
            title="[bold dim]▸ Log Output[/]",
            border_style="dim",
            height=12,
            subtitle=f"[dim]{len(self.log_lines)} lines total[/]",
            subtitle_align="right",
        )

    def _render_summary(self) -> Panel:
        """Render summary panel with stage stats, findings, and errors."""
        total_stages = len(self.stages)
        completed = sum(1 for s in self.stages.values() if s.total > 0 and s.completed >= s.total)
        failed = sum(1 for s in self.stages.values() if not s.success)
        total_time = self.elapsed_seconds

        # Determine overall status
        if total_stages == 0:
            status_text = "[yellow]No stages executed[/]"
            status_label = "Idle"
            border = "yellow"
        elif completed == total_stages:
            status_text = "[bold green]All stages passed[/]"
            status_label = "Complete"
            border = "green"
        elif failed > 0:
            status_text = f"[bold red]{failed} stage(s) failed[/]"
            status_label = "Partial"
            border = "yellow"
        else:
            status_text = "[yellow]In progress...[/]"
            status_label = "Running"
            border = "yellow"

        running = total_stages - completed - failed
        stats = (
            f"  {status_text}\n"
            f"  Stages: [green]{completed}[/] passed "
            f"/ [red]{failed}[/] failed "
            f"/ [dim]{running}[/] running\n"
            f"  Findings: {len(self.findings)}\n"
            f"  Errors: {len(self.errors)}\n"
            f"  Elapsed: {total_time:.1f}s"
        )

        return Panel(
            stats,
            title=f"[bold {border}]{status_label}[/]",
            border_style=border,
        )

    def render(self) -> Group:
        """Render the full display as a Rich Group."""
        children: list[Any] = [
            self._render_stage_table(),
            Rule(),
        ]
        # Findings (if any)
        if self.findings:
            children.append(self._render_findings_table())

        # Errors (if any)
        errors_panel = self._render_errors_panel()
        if errors_panel:
            children.append(errors_panel)

        # Summary
        children.append(self._render_summary())

        return Group(*children)  # type: ignore[misc, arg-type]

    def render_full(self) -> Group:
        """Render the full display including log."""
        children: list[Any] = [
            self._render_stage_table(),
            Rule(),
        ]
        if self.findings:
            children.append(self._render_findings_table())
        errors_panel = self._render_errors_panel()
        if errors_panel:
            children.append(errors_panel)
        children.append(self._render_summary())
        children.append(self._render_log_panel())
        return Group(*children)  # type: ignore[misc, arg-type]


# ── Commands ─────────────────────────────────────────────────────────────────


@app.command("start")
def recon_start(
    target_name: str = typer.Argument(..., help="Target name to run recon against"),
    recipe: str | None = typer.Option(None, "-r", "--recipe", help="Recipe identifier"),
    name: str = typer.Option("recon", "-n", "--name", help="Task name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without executing"),
    live: bool = typer.Option(True, "--live/--no-live", help="Enable live progress display"),
) -> None:
    """Run a recon task against a target with rich progress display."""
    display = ReconDisplay()
    display.add_log(f"[dim]Target:[/dim] {target_name}")
    display.add_log(f"[dim]Recipe:[/dim] {recipe or 'defaults'}")
    display.add_log("")

    # Live display context manager
    context: Any = None
    try:
        if live:
            context = Live(
                display.render_full(), console=console, refresh_per_second=4, screen=False
            )
            context.start()

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
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            stages = _build_stages(recipe)

            if dry_run:
                console.print("[blue]--[/] Dry run mode — no stages executed.")
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                session.add(task)
                session.commit()
                if live:
                    context.stop()
                console.print(Panel("[green]OK[/] Dry run complete.", border_style="green"))
                return

            # ── Execute with Executor engine ─────────────────────────
            executor = Executor(max_concurrent=4, io_workers=8)

            async def _run() -> list[dict[str, Any]]:
                # Register event handler for live display updates
                executor.on_event(display.on_event)

                task_id = str(task.id)
                await executor.submit(
                    task_id=task_id,
                    target_name=target_name,
                    stages=stages,
                )

                # Wait for task to complete
                while True:
                    results = executor.get_task_results(task_id)
                    if results is not None:
                        break
                    await asyncio.sleep(0.1)

                return [r.to_dict() for r in results]

            results = asyncio.run(_run())

            # Update task status
            if results:
                all_success = all(r.get("success", False) for r in results)
                task.status = TaskStatus.COMPLETED if all_success else TaskStatus.FAILED
            else:
                task.status = TaskStatus.FAILED

            task.completed_at = time.time()
            session.add(task)
            session.commit()

        if live:
            context.stop()
            console.print()

    except typer.Exit:
        raise
    except Exception as exc:
        if live and context is not None:
            context.stop()
        console.print(f"[red]Error: {exc}[/]")
        raise typer.Exit(code=1) from exc


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
