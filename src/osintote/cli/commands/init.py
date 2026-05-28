# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Init command — bootstrap the OSINTote project."""

import sys
from pathlib import Path

from typer import Typer

_app = Typer()


@_app.command()
def init(
    force: bool = False,
    db_path: str = "osintote.db",
) -> None:
    """Initialize OSINTote project."""
    import typer

    force = typer.Option(force, "--force", help="Overwrite existing files")
    db_path = typer.Option(db_path, "--db-path", "-d", help="Path to the SQLite database file")
    _init_project(db_path, force)


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
            console.print("[bold green][/] Aborted.")
            sys.exit(0)

    # Create .osintote directory
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
        console.print(f"[green]✓[/] Created [dim]{config_dir}[/]")
    else:
        console.print(f"[blue]•[/] [dim]{config_dir}[/] already exists")

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
        console.print(f"[green]✓[/] Created [dim]{config_file}[/]")

    # Initialize database
    try:
        from osintote.models.database import auto_migrate, init_db
        import asyncio

        console.print(f"[blue]•[/] Database file: [dim]{db_file}[/]")

        if not db_file.exists() or force:
            # Use sync engine for initial table creation
            from sqlalchemy import create_engine as sync_create_engine

            sync_url = f"sqlite:///{db_file}"
            sync_engine = sync_create_engine(sync_url)
            init_db()
            console.print(f"[green]✓[/] Database initialized at [dim]{db_file}[/]")
        else:
            console.print(f"[blue]•[/] Database exists at [dim]{db_file}[/]")

        # Run migrations
        asyncio.run(auto_migrate())
        console.print("[green]✓[/] Migrations applied")

    except ImportError as e:
        console.print(f"[red]✗[/] Failed to import models: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/] Database error: {e}")
        sys.exit(1)

    # Summary
    console.print(
        Panel(
            "[bold green]OSINTote initialized successfully![/]\n\n"
            "  Next steps:\n"
            "    [dim]osintote serve[/]    — Start the web server\n"
            "    [dim]osintote status[/]  — Check system status\n",
            title="✅ Ready",
            border_style="green",
        )
    )
