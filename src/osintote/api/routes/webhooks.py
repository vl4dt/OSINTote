# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Webhook API routes.

Endpoints:
    POST   /api/webhooks       — Create a webhook
    GET    /api/webhooks       — List active webhooks
    GET    /api/webhooks/{id}  — Get webhook
    PUT    /api/webhooks/{id}  — Update webhook
    DELETE /api/webhooks/{id}  — Delete webhook
    POST   /api/webhooks/{id}/test — Test delivery
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from osintote.models.database import get_async_session
from osintote.models.orm import WebhookEvent
from osintote.notify.webhook_manager import WebhookManager

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# ── Schemas ─────────────────────────────────────────────────────────────────


class WebhookCreate(BaseModel):
    """Request body for creating a webhook."""

    name: str
    url: str
    events: list[str]
    secret: str | None = None
    enabled: bool = True


class WebhookUpdate(BaseModel):
    """Request body for updating a webhook."""

    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    enabled: bool | None = None


class WebhookTestRequest(BaseModel):
    """Request body for testing a webhook delivery."""

    event_type: str = "on_task_complete"
    payload: dict[str, Any] = {
        "task_id": "test-001",
        "target_name": "example.com",
    }


# ── Routes ──────────────────────────────────────────────────────────────────


@router.post("", response_model=dict)
async def create_webhook(
    body: WebhookCreate,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Create a new webhook subscription."""
    valid_events = {e.value for e in WebhookEvent}
    invalid = [e for e in body.events if e not in valid_events]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event types: {invalid}. Valid: {list(valid_events)}",
        )

    manager = WebhookManager(db)
    webhook = manager.add(
        name=body.name,
        url=body.url,
        events=body.events,
        secret=body.secret,
        enabled=body.enabled,
    )

    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "enabled": webhook.enabled,
    }


@router.get("", response_model=list[dict])
async def list_webhooks(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> list[dict]:
    """List all active webhooks."""
    manager = WebhookManager(db)
    webhooks = manager.list_active()

    return [
        {
            "id": str(w.id),
            "name": w.name,
            "url": w.url,
            "events": w.events,
            "enabled": w.enabled,
        }
        for w in webhooks
    ]


@router.get("/{webhook_id}", response_model=dict)
async def get_webhook(
    webhook_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Get a webhook by ID."""
    manager = WebhookManager(db)
    webhook = manager.get(uuid.UUID(webhook_id))

    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "enabled": webhook.enabled,
    }


@router.put("/{webhook_id}", response_model=dict)
async def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Update a webhook."""
    manager = WebhookManager(db)
    webhook = manager.get(uuid.UUID(webhook_id))

    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    update_kwargs = {
        k: v for k, v in body.model_dump().items() if v is not None
    }

    # Validate event types if provided
    if "events" in update_kwargs:
        valid_events = {e.value for e in WebhookEvent}
        invalid = [e for e in update_kwargs["events"] if e not in valid_events]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event types: {invalid}",
            )

    webhook = manager.update(webhook, **update_kwargs)

    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "enabled": webhook.enabled,
    }


@router.delete("/{webhook_id}", response_model=dict)
async def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Delete a webhook."""
    manager = WebhookManager(db)
    webhook = manager.get(uuid.UUID(webhook_id))

    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    manager.delete(webhook)
    return {"status": "deleted", "id": webhook_id}


@router.post("/{webhook_id}/test", response_model=dict)
async def test_webhook(
    webhook_id: str,
    body: WebhookTestRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Test delivery to a webhook."""
    manager = WebhookManager(db)
    webhook = manager.get(uuid.UUID(webhook_id))

    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    try:
        result = await manager.deliver(
            body.event_type,
            body.payload,
        )
        return {
            "status": "sent",
            "webhook": webhook.name,
            "event": body.event_type,
            "deliveries": result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Delivery failed: {exc!s}",
        ) from exc
