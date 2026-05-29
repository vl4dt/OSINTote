# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the webhook manager."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from osintote.notify.webhook_manager import WebhookManager

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _mock_http_client(response_status=200) -> MagicMock:
    """Create a mock HTTP client with async context manager support."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# ── CRUD tests ──────────────────────────────────────────────────────────────


class TestWebhookManagerCRUD:
    """Tests for WebhookManager CRUD operations."""

    def test_add(self, db_session: Session) -> None:
        """Add should create a webhook."""
        manager = WebhookManager(db_session)
        webhook = manager.add("test", "https://example.com/webhook", ["on_task_complete"])
        assert webhook is not None
        assert webhook.name == "test"
        assert webhook.url == "https://example.com/webhook"
        assert "on_task_complete" in webhook.events
        assert webhook.enabled is True

    def test_add_with_secret(self, db_session: Session) -> None:
        """Add should store secret."""
        manager = WebhookManager(db_session)
        webhook = manager.add(
            "test", "https://example.com/webhook",
            ["on_task_complete"], secret="my-secret"
        )
        assert webhook.secret == "my-secret"

    def test_get(self, db_session: Session) -> None:
        """Get should return webhook by ID."""
        manager = WebhookManager(db_session)
        webhook = manager.add("test", "https://example.com/webhook", ["on_task_complete"])
        retrieved = manager.get(webhook.id)
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_get_not_found(self, db_session: Session) -> None:
        """Get should return None for invalid ID."""
        import uuid
        manager = WebhookManager(db_session)
        retrieved = manager.get(uuid.uuid4())
        assert retrieved is None

    def test_list_active(self, db_session: Session) -> None:
        """List active should return only enabled webhooks."""
        manager = WebhookManager(db_session)
        manager.add("active", "https://example.com/1", ["on_task_complete"], enabled=True)
        manager.add("disabled", "https://example.com/2", ["on_task_complete"], enabled=False)
        webhooks = manager.list_active()
        assert len(webhooks) == 1
        assert webhooks[0].name == "active"

    def test_update(self, db_session: Session) -> None:
        """Update should modify webhook fields."""
        manager = WebhookManager(db_session)
        webhook = manager.add("old-name", "https://example.com", ["on_task_complete"])
        updated = manager.update(webhook, name="new-name", enabled=False)
        assert updated.name == "new-name"
        assert updated.enabled is False

    def test_delete(self, db_session: Session) -> None:
        """Delete should remove webhook."""
        manager = WebhookManager(db_session)
        webhook = manager.add("test", "https://example.com", ["on_task_complete"])
        manager.delete(webhook)
        assert manager.get(webhook.id) is None


# ── Delivery tests ─────────────────────────────────────────────────────────


class TestWebhookManagerDelivery:
    """Tests for WebhookManager delivery."""

    @pytest.mark.asyncio
    async def test_deliver_single_webhook(self, db_session: Session) -> None:
        """Deliver should send to matching webhooks."""
        manager = WebhookManager(db_session)
        manager.add("test", "https://example.com/webhook", ["on_task_complete"])

        mock_client = _mock_http_client()
        result = await manager.deliver("on_task_complete", {"task_id": "123"}, http_client=mock_client)  # noqa: E501
        assert result == 1

    @pytest.mark.asyncio
    async def test_deliver_no_match(self, db_session: Session) -> None:
        """Deliver should return 0 for non-matching event."""
        manager = WebhookManager(db_session)
        manager.add("test", "https://example.com/webhook", ["on_task_complete"])

        result = await manager.deliver("on_task_fail", {"task_id": "123"})
        assert result == 0

    @pytest.mark.asyncio
    async def test_deliver_multiple_webhooks(self, db_session: Session) -> None:
        """Deliver should send to all matching webhooks."""
        manager = WebhookManager(db_session)
        manager.add("test1", "https://example.com/1", ["on_task_complete"])
        manager.add("test2", "https://example.com/2", ["on_task_complete"])

        mock_client = _mock_http_client()
        result = await manager.deliver("on_task_complete", {"task_id": "123"}, http_client=mock_client)  # noqa: E501
        assert result == 2

    @pytest.mark.asyncio
    async def test_deliver_failure(self, db_session: Session) -> None:
        """Deliver should handle failures gracefully."""
        manager = WebhookManager(db_session)
        manager.add("test", "https://example.com/webhook", ["on_task_complete"])

        mock_response = MagicMock()
        mock_response.raise_for_status = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())  # noqa: E501

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        result = await manager.deliver("on_task_complete", {"task_id": "123"}, http_client=mock_client)  # noqa: E501
        assert result == 0

    @pytest.mark.asyncio
    async def test_deliver_task_complete(self, db_session: Session) -> None:
        """Deliver task complete should create correct payload."""
        manager = WebhookManager(db_session)
        manager.add("test", "https://example.com/webhook", ["on_task_complete"])

        mock_client = _mock_http_client()
        result = await manager.deliver_task_complete("task-123", "example.com", {"extra": "data"}, http_client=mock_client)  # noqa: E501
        assert result == 1

    @pytest.mark.asyncio
    async def test_deliver_task_fail(self, db_session: Session) -> None:
        """Deliver task fail should create correct payload."""
        manager = WebhookManager(db_session)
        manager.add("test", "https://example.com/webhook", ["on_task_fail"])

        mock_client = _mock_http_client()
        result = await manager.deliver_task_fail("task-123", "example.com", "Error occurred", http_client=mock_client)  # noqa: E501
        assert result == 1

    @pytest.mark.asyncio
    async def test_deliver_critical_finding(self, db_session: Session) -> None:
        """Deliver critical finding should create correct payload."""
        manager = WebhookManager(db_session)
        manager.add("test", "https://example.com/webhook", ["on_critical_finding"])

        mock_client = _mock_http_client()
        result = await manager.deliver_critical_finding({"finding": "critical CVE"}, http_client=mock_client)  # noqa: E501
        assert result == 1


# ── HMAC signing test ──────────────────────────────────────────────────────


class TestWebhookManagerSigning:
    """Tests for HMAC-SHA256 webhook signing."""

    @pytest.mark.asyncio
    async def test_hmac_signature(self, db_session: Session) -> None:
        """Webhook with secret should include HMAC signature."""
        manager = WebhookManager(db_session)
        manager.add(
            "test", "https://example.com/webhook",
            ["on_task_complete"], secret="my-secret"
        )

        import hashlib
        import hmac

        payload = {"task_id": "123"}
        body = json.dumps(payload).encode("utf-8")
        expected_sig = hmac.new(b"my-secret", body, hashlib.sha256).hexdigest()

        captured_headers = {}
        async def capture_post(url, content, headers, timeout):
            captured_headers.update(headers)
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            return mock_response

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=capture_post)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        await manager.deliver("on_task_complete", payload, http_client=mock_client)

        assert "X-Webhook-Signature" in captured_headers
        assert captured_headers["X-Webhook-Signature"] == f"sha256={expected_sig}"
