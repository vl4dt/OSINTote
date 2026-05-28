# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Status command — show OSINTote system status."""

import sys
from pathlib import Path

import typer
from sqlmodel import Session, text
from sqlalchemy import create_engine


@typer.command()
def status() -> None:
    """Show OSINTote system status."""
    _status()


def _status() -> None:
    """Display OSINTote system status."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    # Database check
    db_path = Path.cwd() / "osintote.db"
    db_exists = db_path.exists()

    if db_exists:
        stats = _get_db_stats(db_path)
    else:
        stats = {"targets": 0, "records": 0, "tasks": 0, "api_keys": 0, "webhooks": 0, "settings": 0}

    # Version
    try:
        from osintote.__about__ import __version__

        version = __version__
    except ImportError:
        version = "unknown"

    # Project root
    project_root = Path.cwd()

    # Print summary
    console.print()
    console.print(
        Panel(
            f"[bold]Version[/]: [cyan]{version}[/]\n"
            f"[bold]Project[/]: [dim]{project_root}[/]\n"
            f"[bold]Database[/]: {'[green]Exists[/]' if db_exists else '[red]Not found[/]'}\n",
            title="OSINTote",
            border_style="blue",
        )
    )

    console.print()
    stats_table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
    )
    stats_table.add_row("[bold]Database[/]", f"[dim]{db_path}[/]" if db_exists else "[red]Not initialized[/]")
    stats_table.add_row("Targets", str(stats["targets"]))
    stats_table.add_row("Records", str(stats["records"]))
    stats_table.add_row("Tasks", str(stats["tasks"]))
    stats_table.add_row("API Keys", str(stats["api_keys"]))
    stats_table.add_row("Webhooks", str(stats["webhooks"]))
    stats_table.add_row("Settings", str(stats["settings"]))

    console.print(Panel(stats_table, title="Data Summary", border_style="green"))

    if not db_exists:
        console.print()
        console.print("[yellow]Tip:[/] Run [dim]osintote init[/] to create the database.")


def _get_db_stats(db_path: Path) -> dict[str, int]:
    """Query database for entity counts."""
    try:
        engine = create_engine(f"sqlite:///{db_path}")
        with Session(engine) as session:
            return {
                "targets": session.exec(text("SELECT COUNT(*) FROM targets")).one(),
                "records": session.exec(text("SELECT COUNT(*) FROM records")).one(),
                "tasks": session.exec(text("SELECT COUNT(*) FROM tasks")).one(),
                "api_keys": session.exec(text("SELECT COUNT(*) FROM api_keys")).one(),
                "webhooks": session.exec(text("SELECT COUNT(*) FROM webhooks")).one(),
                "settings": session.exec(text("SELECT COUNT(*) FROM settings")).one(),
            }
    except Exception:
        return {
            "targets": 0,
            "records": 0,
            "tasks": 0,
            "api_keys": 0,
            "webhooks": 0,
            "settings": 0,
        }
