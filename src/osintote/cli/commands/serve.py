# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Serve command — start the OSINTote web server."""

import asyncio

import typer


@typer.command()
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Host to bind the server to",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to bind the server to",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Enable auto-reload for development",
    ),
) -> None:
    """Start the OSINTote web server."""
    _serve(host, port, reload)


def _serve(host: str, port: int, reload: bool) -> None:
    """Start the uvicorn web server."""
    import uvicorn
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print(f"[blue]•[/] Starting server at [dim]http://{host}:{port}[/]")

    # Run migrations before starting
    try:
        from osintote.models.database import auto_migrate

        asyncio.run(auto_migrate())
        console.print("[green]✓[/] Migrations applied")
    except Exception as e:
        console.print(f"[yellow]⚠[/] Migration warning: {e}")

    # Configure uvicorn
    uvicorn.run(
        "osintote.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
