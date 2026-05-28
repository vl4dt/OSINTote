# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""OSINTote CLI — entry point."""

import asyncio
import sys
from pathlib import Path

from osintote.__about__ import __version__
from typer import Option, Typer

app = Typer(
    name="osintote",
    help="Ultimate OSINT tool with AI-powered analysis, CLI + Web UI",
    add_help_option=True,
    pretty_exceptions_enable=False,
    rich_markup_mode="rich",
)


def _init_project(db_path: str, force: bool) -> None:
    """Bootstrap the OSINTote project."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm

    console = Console()
    project_root = Path.cwd()
    db_file = project_root / db_path
    config_dir = project_root / ".osintote"
    config_file = config_dir / "config.json"

    # Check for existing config
    if config_file.exists() and not force:
        overwrite = Confirm.ask(
            f"[yellow]Config file already exists at {config_file}[/]. Overwrite?",
            default=False,
        )
        if not overwrite:
            console.print("[bold green]Aborted.[/]")
            sys.exit(0)

    # Create .osintote directory
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
        console.print("[green]OK[/] Created [dim]{path}[/]".format(path=config_dir))
    else:
        console.print("[blue]--[/] [dim]{path}[/] already exists".format(path=config_dir))

    # Create default config
    if not config_file.exists() or force:
        config_dir.mkdir(parents=True, exist_ok=True)
        default_config = {
            "version": "0.0.1",
            "database": db_path,
            "listen_host": "127.0.0.1",
            "listen_port": 8000,
        }
        config_file.write_text(
            f'{{\n  "version": "{default_config["version"]}",\n'
            f'  "database": "{default_config["database"]}",\n'
            f'  "listen_host": "{default_config["listen_host"]}",\n'
            f'  "listen_port": {default_config["listen_port"]}\n'
            "}\n"
        )
        console.print("[green]OK[/] Created [dim]{path}[/]".format(path=config_file))

    # Initialize database
    try:
        from osintote.models.database import auto_migrate

        console.print("[blue]--[/] Database file: [dim]{path}[/]".format(path=db_file))

        if db_file.exists() and not force:
            console.print("[blue]--[/] Database exists at [dim]{path}[/]".format(path=db_file))
        else:
            console.print("[blue]--[/] Creating new database at [dim]{path}[/]".format(path=db_file))

        asyncio.run(auto_migrate())
        console.print("[green]OK[/] Migrations applied")

    except ImportError as e:
        console.print("[red]FAIL[/] Failed to import models: {e}".format(e=e))
        sys.exit(1)
    except Exception as e:
        console.print("[red]FAIL[/] Database error: {e}".format(e=e))
        sys.exit(1)

    # Summary
    console.print(
        Panel(
            "[bold green]OSINTote initialized successfully![/]\n\n"
            "  Next steps:\n"
            "    [dim]osintote serve[/]    - Start the web server\n"
            "    [dim]osintote status[/]  - Check system status\n",
            title="Ready",
            border_style="green",
        )
    )


def _status() -> None:
    """Display OSINTote system status."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from sqlmodel import Session, text
    from sqlalchemy import create_engine

    console = Console()

    # Database check
    db_path = Path.cwd() / "osintote.db"
    db_exists = db_path.exists()

    if db_exists:
        try:
            engine = create_engine(f"sqlite:///{db_path}")
            with Session(engine) as session:
                stats = {
                    "targets": session.scalar(text("SELECT COUNT(*) FROM targets")),
                    "records": session.scalar(text("SELECT COUNT(*) FROM records")),
                    "tasks": session.scalar(text("SELECT COUNT(*) FROM tasks")),
                    "api_keys": session.scalar(text("SELECT COUNT(*) FROM api_keys")),
                    "webhooks": session.scalar(text("SELECT COUNT(*) FROM webhooks")),
                    "settings": session.scalar(text("SELECT COUNT(*) FROM settings")),
                }
        except Exception:
            stats = {"targets": 0, "records": 0, "tasks": 0, "api_keys": 0, "webhooks": 0, "settings": 0}
    else:
        stats = {"targets": 0, "records": 0, "tasks": 0, "api_keys": 0, "webhooks": 0, "settings": 0}

    # Version
    try:
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


@app.command()
def init(
    force: bool = Option(False, "--force", help="Overwrite existing files"),
    db_path: str = Option("osintote.db", "--db-path", "-d", help="Path to the SQLite database file"),
) -> None:
    """Initialize OSINTote project."""
    _init_project(db_path, force)


@app.command()
def serve(
    host: str = Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = Option(False, "--reload", "-r", help="Enable auto-reload for development"),
) -> None:
    """Start the OSINTote web server."""
    import uvicorn
    from rich.console import Console

    console = Console()
    console.print("[blue]--[/] Starting server at [dim]http://{host}:{port}[/]".format(host=host, port=port))

    # Run migrations before starting
    try:
        from osintote.models.database import auto_migrate

        asyncio.run(auto_migrate())
        console.print("[green]OK[/] Migrations applied")
    except Exception as e:
        console.print("[yellow]WARN[/] Migration warning: {e}".format(e=e))

    uvicorn.run(
        "osintote.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@app.command()
def status() -> None:
    """Show OSINTote system status."""
    _status()


def main() -> None:
    """CLI entry point."""
    app()
