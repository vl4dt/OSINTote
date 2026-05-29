# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Settings command — manage OSINTote settings."""

from __future__ import annotations

from typing import Any

import typer
from typer import BadParameter, Option, Typer

_app = Typer()


@_app.command()
def get(key: str) -> None:
    """Get a setting value."""
    from osintote.models.database import get_session
    from osintote.models.orm import Setting

    with get_session() as session:
        setting = session.query(Setting).filter(Setting.key == key).first()
        if setting is None:
            raise BadParameter(f"Setting '{key}' not found")
        typer.echo(setting.value)


@_app.command()
def set(
    key: str,
    value: str,
    description: str | None = None,
) -> None:
    """Set a setting value."""
    import json

    from osintote.models.database import get_session
    from osintote.models.orm import Setting

    # Try to parse value as JSON, otherwise treat as string
    try:
        parsed_value: Any = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    with get_session() as session:
        setting = session.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = parsed_value
            if description:
                setting.description = description
        else:
            setting = Setting(key=key, value=parsed_value, description=description)
            session.add(setting)
        session.commit()
        typer.echo(f"Setting '{key}' updated")


@_app.command()
def list() -> None:
    """List all settings."""
    from rich.console import Console
    from rich.table import Table

    from osintote.models.database import get_session
    from osintote.models.orm import Setting

    console = Console()
    table = Table(title="OSINTote Settings")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")

    with get_session() as session:
        settings = session.query(Setting).all()
        for setting in settings:
            table.add_row(
                setting.key,
                str(setting.value),
                setting.description or "",
            )

    console.print(table)


@_app.command()
def notifications(
    enable: bool = Option(
        True,
        "--enable/--disable",
        "-e/-d",
        help="Enable or disable desktop notifications",
    ),
) -> None:
    """Toggle desktop notifications."""
    from rich.console import Console

    from osintote.models.database import get_session
    from osintote.models.orm import Setting

    console = Console()
    with get_session() as session:
        setting = session.query(Setting).filter(Setting.key == "notifications").first()
        value = {"enabled": enable}
        if setting:
            setting.value = value
        else:
            setting = Setting(
                key="notifications",
                value=value,
                description="Desktop notifications toggle",
            )
            session.add(setting)
        session.commit()

    status = "enabled" if enable else "disabled"
    console.print(f"[green]✓[/] Desktop notifications {status}")
