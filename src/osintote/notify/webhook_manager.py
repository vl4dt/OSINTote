# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Webhook manager — CRUD and delivery for webhook subscriptions.

Provides :class:`WebhookManager` which:
  - creates/updates/deletes webhooks from the database
  - delivers events to active webhooks with HMAC-SHA256 signing
  - integrates with the event system (on_task_complete, etc.)

Usage::

    manager = WebhookManager(session)
    await manager.add(
        "github", "https://hooks.slack.com/...",
        ["on_task_complete"], secret="my-secret"
    )
    await manager.deliver(
        "on_task_complete", {"task_id": "...", "target": "example.com"}
    )
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from httpx import AsyncClient
from sqlalchemy.orm import Session

from osintote.models.orm import Webhook, WebhookEvent

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manage webhook subscriptions and deliveries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── CRUD ──────────────────────────────────────────────────────────

    def add(
        self,
        name: str,
        url: str,
        events: list[str],
        secret: str | None = None,
        enabled: bool = True,
    ) -> Webhook:
        """Create a new webhook subscription.

        Parameters
        ----------
        name:
            Human-readable webhook name.
        url:
            HTTP(S) endpoint URL.
        events:
            List of :class:`WebhookEvent` values to subscribe to.
        secret:
            HMAC-SHA256 signing secret.
        enabled:
            Whether the webhook is active.
        """
        webhook = Webhook(
            name=name,
            url=url,
            events=events,
            secret=secret,
            enabled=enabled,
        )
        self.session.add(webhook)
        self.session.commit()
        self.session.refresh(webhook)
        logger.info("Webhook added: %s → %s [%s]", name, url, ",".join(events))
        return webhook

    def get(self, webhook_id: Any) -> Webhook | None:
        """Retrieve a webhook by ID."""
        return self.session.get(Webhook, webhook_id)

    def list_active(self) -> list[Webhook]:
        """Return all enabled webhooks."""
        return list(
            self.session.query(Webhook).filter(Webhook.enabled).all()
        )

    def update(self, webhook: Webhook, **kwargs: Any) -> Webhook:
        """Update a webhook's fields."""
        for key, value in kwargs.items():
            if hasattr(webhook, key) and value is not None:
                setattr(webhook, key, value)
        self.session.commit()
        self.session.refresh(webhook)
        logger.info("Webhook updated: %s", webhook.name)
        return webhook

    def delete(self, webhook: Webhook) -> None:
        """Delete a webhook."""
        logger.info("Webhook deleted: %s", webhook.name)
        self.session.delete(webhook)
        self.session.commit()

    # ── Delivery ─────────────────────────────────────────────────────

    async def deliver(
        self,
        event_type: str,
        payload: dict[str, Any],
        http_client: AsyncClient | None = None,
    ) -> int:
        """Deliver an event to all matching webhooks.

        Returns the number of webhooks that received the event.
        """
        webhooks = [w for w in self.list_active() if event_type in w.events]
        if not webhooks:
            return 0

        delivered = 0
        async with http_client or AsyncClient() as client:
            for webhook in webhooks:
                try:
                    await self._deliver_to(
                        client,
                        webhook,
                        event_type,
                        payload,
                    )
                    delivered += 1
                except Exception as exc:
                    logger.error("Webhook delivery failed for %s: %s", webhook.name, exc)

        total = len(webhooks)
        logger.info(
            "Webhook delivered %s event to %d/%d targets",
            event_type, delivered, total,
        )
        return delivered

    async def deliver_event(
        self,
        event: WebhookEvent,
        payload: dict[str, Any],
        http_client: AsyncClient | None = None,
    ) -> int:
        """Deliver a :class:`WebhookEvent` typed event."""
        return await self.deliver(event.value, payload, http_client)

    async def deliver_task_complete(
        self,
        task_id: str,
        target_name: str,
        extra: dict[str, Any] | None = None,
        http_client: AsyncClient | None = None,
    ) -> int:
        """Deliver an ON_TASK_COMPLETE event."""
        payload = {
            "event": "on_task_complete",
            "task_id": task_id,
            "target_name": target_name,
            "extra": extra or {},
            "timestamp": __import__("datetime", fromlist=["datetime"]).datetime.now().isoformat(),
        }
        return await self.deliver("on_task_complete", payload, http_client)

    async def deliver_task_fail(
        self,
        task_id: str,
        target_name: str,
        error_message: str | None = None,
        http_client: AsyncClient | None = None,
    ) -> int:
        """Deliver an ON_TASK_FAIL event."""
        payload = {
            "event": "on_task_fail",
            "task_id": task_id,
            "target_name": target_name,
            "error_message": error_message or "",
            "timestamp": __import__("datetime", fromlist=["datetime"]).datetime.now().isoformat(),
        }
        return await self.deliver("on_task_fail", payload, http_client)

    async def deliver_critical_finding(
        self,
        finding: dict[str, Any],
        http_client: AsyncClient | None = None,
    ) -> int:
        """Deliver an ON_CRITICAL_FINDING event."""
        payload = {
            "event": "on_critical_finding",
            "finding": finding,
            "timestamp": __import__("datetime", fromlist=["datetime"]).datetime.now().isoformat(),
        }
        return await self.deliver("on_critical_finding", payload, http_client)

    # ── Private helpers ───────────────────────────────────────────────

    async def _deliver_to(
        self,
        client: AsyncClient,
        webhook: Webhook,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Send a single webhook delivery with HMAC-SHA256 signing."""
        body = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "X-Event-Type": event_type,
            "X-OSINTOTE-Version": "0.1.0",
        }

        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        response = await client.post(
            webhook.url,
            content=body,
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
