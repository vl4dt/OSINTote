# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""CLI webhook commands.

Subcommands:
    add     — Add a new webhook
    list    — List active webhooks
    delete  — Delete a webhook
    test    — Test webhook delivery
"""

from __future__ import annotations

import sys
from typing import Any

import typer

from osintote.models.orm import WebhookEvent

webhook_app = typer.Typer(
    name="webhook",
    help="Manage webhook subscriptions",
    no_args_is_help=True,
)


VALID_EVENTS = [e.value for e in WebhookEvent]


@webhook_app.command()
def add(
    name: str = typer.Argument(..., help="Webhook name"),
    url: str = typer.Argument(..., help="Webhook endpoint URL"),
    events: str = typer.Option(
        "on_task_complete",
        "--events",
        "-e",
        help=f"Comma-separated event types: {','.join(VALID_EVENTS)}",
    ),
    secret: str | None = typer.Option(
        None,
        "--secret",
        "-s",
        help="HMAC-SHA256 signing secret",
    ),
    enabled: bool = typer.Option(
        True,
        "--enabled/--disabled",
        help="Enable or disable the webhook",
    ),
) -> None:
    """Add a new webhook subscription."""
    from sqlmodel import Session

    from osintote.cli.commands.init import get_engine
    from osintote.notify.webhook_manager import WebhookManager

    engine = get_engine()
    with Session(engine) as session:
        event_list = [e.strip() for e in events.split(",") if e.strip()]
        invalid = [e for e in event_list if e not in VALID_EVENTS]
        if invalid:
            typer.echo(f"Invalid event types: {invalid}")
            typer.echo(f"Valid events: {','.join(VALID_EVENTS)}")
            sys.exit(1)

        manager = WebhookManager(session)
        webhook = manager.add(
            name=name,
            url=url,
            events=event_list,
            secret=secret,
            enabled=enabled,
        )
        typer.echo(f"Webhook added: {webhook.name} → {webhook.url}")
        typer.echo(f"  Events: {','.join(webhook.events)}")
        typer.echo(f"  Enabled: {webhook.enabled}")


@webhook_app.command()
def list_(
    all_: bool = typer.Option(False, "--all", "-a", help="Show all webhooks (including disabled)"),
) -> None:
    """List active webhooks."""
    from sqlmodel import Session

    from osintote.cli.commands.init import get_engine
    from osintote.notify.webhook_manager import WebhookManager

    engine = get_engine()
    with Session(engine) as session:
        manager = WebhookManager(session)
        from osintote.models.orm import Webhook
        webhooks = (
            manager.list_active()
            if not all_
            else session.query(Webhook).all()
        )

        if not webhooks:
            typer.echo("No webhooks found.")
            return

        typer.echo(f"{'Name':<20} {'URL':<40} {'Events':<30} {'Enabled'}")
        typer.echo("-" * 90)
        for w in webhooks:
            url_short = w.url[:37] + '...' if len(w.url) > 40 else w.url
            events = ",".join(w.events)
            typer.echo(f"{w.name:<20} {url_short:<40} {events:<30} {w.enabled}")


@webhook_app.command()
def delete(
    webhook_id: str = typer.Argument(..., help="Webhook ID"),
) -> None:
    """Delete a webhook."""
    import uuid as uuid_module

    from sqlmodel import Session

    from osintote.cli.commands.init import get_engine
    from osintote.models.orm import Webhook
    from osintote.notify.webhook_manager import WebhookManager

    engine = get_engine()
    with Session(engine) as session:
        manager = WebhookManager(session)
        webhook = session.get(Webhook, uuid_module.UUID(webhook_id))

        if webhook is None:
            typer.echo(f"Webhook not found: {webhook_id}")
            sys.exit(1)

        manager.delete(webhook)
        typer.echo(f"Webhook deleted: {webhook.name}")


@webhook_app.command()
def test(
    webhook_id: str = typer.Argument(..., help="Webhook ID"),
    event_type: str = typer.Option(
        "on_task_complete",
        "--event",
        "-e",
        help="Event type to test",
    ),
) -> None:
    """Test webhook delivery."""
    import asyncio
    import uuid as uuid_module

    from sqlmodel import Session

    from osintote.cli.commands.init import get_engine
    from osintote.models.orm import Webhook
    from osintote.notify.webhook_manager import WebhookManager

    engine = get_engine()
    with Session(engine) as session:
        manager = WebhookManager(session)
        webhook = session.get(Webhook, uuid_module.UUID(webhook_id))

        if webhook is None:
            typer.echo(f"Webhook not found: {webhook_id}")
            sys.exit(1)

        async def _test() -> None:
            result = await manager.deliver(
                event_type,
                {"task_id": "test-001", "target_name": "example.com"},
            )
            typer.echo(f"Webhook: {webhook.name}")
            typer.echo(f"Event: {event_type}")
            typer.echo(f"Deliveries: {result}/{1}")  # 1 webhook tested

        asyncio.run(_test())


def register(app: Any) -> None:
    """Register the webhook subcommand with the main CLI."""
    app.add_typer(webhook_app, name="webhook")


def main() -> None:
    """CLI entry point."""
    webhook_app()


if __name__ == "__main__":
    main()
