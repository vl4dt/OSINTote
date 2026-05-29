# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""CLI API key commands.

Subcommands:
    add     — Add a new API key
    list    — List all API keys
    rotate  — Rotate primary key for a source
    show    — Show API key details
"""

from __future__ import annotations

import sys
import uuid

import typer

api_key_app = typer.Typer(
    name="api-key",
    help="Manage API keys for external OSINT sources",
    no_args_is_help=True,
)


@api_key_app.command()
def add(
    name: str = typer.Argument(..., help="Key name"),
    source: str = typer.Argument(..., help="Source name (e.g., shodan, virustotal, openai)"),
    key: str = typer.Argument(..., help="API key/credential value"),
    primary: bool = typer.Option(
        False, "--primary", "-p", help="Set as primary key for this source"
    ),
    fallback: bool = typer.Option(
        False, "--fallback", "-f", help="Set as fallback key"
    ),
    target: str | None = typer.Option(
        None, "--target", "-t", help="Associate with a target ID"
    ),
) -> None:
    """Add a new API key for an external OSINT source."""
    from sqlmodel import Session

    from osintote.api.manager import ApiKeyManager
    from osintote.cli.commands.init import get_session as get_db_session

    engine = get_db_session()
    with Session(engine) as session:
        manager = ApiKeyManager(session)

        target_id = None
        if target:
            try:
                target_id = uuid.UUID(target)
            except ValueError:
                typer.echo(f"Invalid target ID: {target}")
                sys.exit(1)

        api_key = manager.add(
            name=name,
            source=source,
            key=key,
            target_id=target_id,
            primary=primary,
            fallback=fallback,
        )

        typer.echo(f"API key added: {api_key.name}")
        typer.echo(f"  Source: {api_key.source}")
        typer.echo(f"  Primary: {api_key.primary}")
        typer.echo(f"  Fallback: {api_key.fallback}")


@api_key_app.command()
def list_(
    source: str | None = typer.Option(
        None, "--source", "-s", help="Filter by source name"
    ),
) -> None:
    """List API keys."""
    from sqlmodel import Session

    from osintote.api.manager import ApiKeyManager
    from osintote.cli.commands.init import get_session as get_db_session

    engine = get_db_session()
    with Session(engine) as session:
        manager = ApiKeyManager(session)

        keys = manager.list_by_source(source) if source else manager.list_all()

        if not keys:
            typer.echo("No API keys found.")
            return

        typer.echo(f"{'Name':<25} {'Source':<15} {'Primary':<8} {'Fallback':<8}")
        typer.echo("-" * 56)
        for k in keys:
            typer.echo(
                f"{k.name:<25} {k.source:<15} "
                f"{'yes' if k.primary else 'no':<8} "
                f"{'yes' if k.fallback else 'no':<8}"
            )


@api_key_app.command()
def show(
    key_id: str = typer.Argument(..., help="API key ID"),
) -> None:
    """Show API key details."""
    from sqlmodel import Session

    from osintote.api.manager import ApiKeyManager
    from osintote.cli.commands.init import get_session as get_db_session

    engine = get_db_session()
    with Session(engine) as session:
        manager = ApiKeyManager(session)
        key = manager.get(uuid.UUID(key_id))

        if key is None:
            typer.echo(f"API key not found: {key_id}")
            sys.exit(1)

        typer.echo(f"Name: {key.name}")
        typer.echo(f"Source: {key.source}")
        typer.echo("Key: ****")
        typer.echo(f"Primary: {key.primary}")
        typer.echo(f"Fallback: {key.fallback}")
        typer.echo(f"Target: {key.target_id}")


@api_key_app.command()
def rotate(
    source: str = typer.Argument(..., help="Source name"),
    key: str = typer.Argument(..., help="New API key value"),
    name: str | None = typer.Option(
        None, "--name", "-n", help="New key name"
    ),
) -> None:
    """Rotate the primary API key for a source."""
    from sqlmodel import Session

    from osintote.api.manager import ApiKeyManager
    from osintote.cli.commands.init import get_session as get_db_session

    engine = get_db_session()
    with Session(engine) as session:
        manager = ApiKeyManager(session)
        rotated = manager.rotate_primary(
            source=source,
            new_key=key,
            new_name=name,
        )

        typer.echo(f"Primary key rotated for {rotated.source}:")
        typer.echo(f"  Name: {rotated.name}")
        typer.echo("  Key: ****")


def register(app: typer.Typer) -> None:
    """Register the api-key subcommand with the main CLI."""
    app.add_typer(api_key_app, name="api-key")


def main() -> None:
    """CLI entry point."""
    api_key_app()


if __name__ == "__main__":
    main()
