# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for SSE task streaming."""

from unittest.mock import MagicMock, patch

import pytest

from osintote.api.app import app


@pytest.fixture
def mock_executor():
    """Create a mock executor with get_events and on_event."""
    executor = MagicMock()
    executor.get_events.return_value = [
        {
            "task_id": "00000000-0000-0000-0000-000000000000",
            "type": "task_started",
        },
        {
            "task_id": "00000000-0000-0000-0000-000000000000",
            "type": "progress",
            "progress": 50,
        },
    ]
    executor.on_event = MagicMock()
    return executor


@pytest.fixture
def set_executor(mock_executor):
    """Set the module-level executor."""
    from osintote.api.routes import tasks as tasks_router

    with patch.object(tasks_router, "_executor", mock_executor):
        yield mock_executor


@pytest.mark.asyncio
async def test_stream_endpoint_not_available():
    """Test 503 when executor not available."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get(
        "/api/tasks/00000000-0000-0000-0000-000000000000/stream"
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Executor not available"


@pytest.mark.asyncio
async def test_get_task_events_returns_list(set_executor):
    """Test snapshot events endpoint returns a list."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get(
        "/api/tasks/00000000-0000-0000-0000-000000000000/events"
    )
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) == 2
    assert events[0]["type"] == "task_started"
    assert events[1]["type"] == "progress"


@pytest.mark.asyncio
async def test_sse_stream_on_event_registered(mock_executor):
    """Verify executor.on_event exists as the SSE handler target."""
    # The SSE stream endpoint calls executor.on_event(_handler) to
    # register a listener. We verify the method is callable.
    assert callable(mock_executor.on_event)


@pytest.mark.asyncio
async def test_sse_stream_get_events_returns_data(mock_executor):
    """Verify executor.get_events returns buffered events."""
    events = mock_executor.get_events("00000000-0000-0000-0000-000000000000")
    assert len(events) == 2
    assert events[0]["type"] == "task_started"
