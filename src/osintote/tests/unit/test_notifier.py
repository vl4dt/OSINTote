# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the Notifier callback system."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from osintote.notify import Notifier
from osintote.notify.notifier import CallbackConfig


class TestCallbackConfig:
    """Tests for CallbackConfig model."""

    def test_default_values(self):
        """Test CallbackConfig default values."""
        cb = CallbackConfig()
        assert cb.command is None
        assert cb.url is None
        assert cb.method == "POST"
        assert cb.headers == {}
        assert cb.enabled is True

    def test_custom_values(self):
        """Test CallbackConfig with custom values."""
        cb = CallbackConfig(
            command="echo hello",
            url="http://localhost:9999",
            method="PUT",
            headers={"X-Custom": "value"},
            enabled=False,
        )
        assert cb.command == "echo hello"
        assert cb.url == "http://localhost:9999"
        assert cb.method == "PUT"
        assert cb.headers == {"X-Custom": "value"}
        assert cb.enabled is False


class TestNotifierInit:
    """Tests for Notifier initialization."""

    def test_default_init(self):
        """Test default Notifier initialization."""
        notifier = Notifier()
        assert notifier.callbacks == []

    def test_init_with_callbacks(self):
        """Test Notifier initialization with callbacks."""
        callbacks = [
            CallbackConfig(command="echo hello"),
            CallbackConfig(url="http://localhost:9999"),
        ]
        notifier = Notifier(callbacks=callbacks)
        assert len(notifier.callbacks) == 2

    def test_add_command(self):
        """Test adding a command callback."""
        notifier = Notifier()
        notifier.add_command("echo hello")
        assert len(notifier.callbacks) == 1
        assert notifier.callbacks[0].command == "echo hello"

    def test_add_webhook(self):
        """Test adding a webhook callback."""
        notifier = Notifier()
        notifier.add_webhook("http://localhost:9999", method="PUT")
        assert len(notifier.callbacks) == 1
        assert notifier.callbacks[0].url == "http://localhost:9999"
        assert notifier.callbacks[0].method == "PUT"


class TestRunCommand:
    """Tests for shell command execution."""

    def test_run_command_empty(self):
        """Test empty command handling."""
        notifier = Notifier()
        result = notifier.run_command("")
        assert result is False

    def test_run_command_invalid_syntax(self):
        """Test invalid command syntax handling."""
        notifier = Notifier()
        result = notifier.run_command("echo 'unclosed")
        assert result is False

    def test_command_placeholder_substitution(self):
        """Test command placeholder substitution logic."""
        cmd = "echo {task_id} {target}"
        task_id = "12345"
        target = "example.com"
        result = cmd.replace("{task_id}", task_id).replace("{target}", target)
        assert result == f"echo {task_id} {target}"


class TestSendWebhook:
    """Tests for webhook sending."""

    @pytest.mark.asyncio
    async def test_send_webhook_success(self, httpx_mock):
        """Test successful webhook delivery."""
        notifier = Notifier()
        httpx_mock.add_response(url="http://localhost:9999/test", json={"status": "ok"})

        result = await notifier.send_webhook(
            "http://localhost:9999/test",
            {"event": "test"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_webhook_failure(self, httpx_mock):
        """Test webhook delivery failure."""
        notifier = Notifier()
        httpx_mock.add_response(url="http://localhost:9999/test", status_code=500)

        result = await notifier.send_webhook(
            "http://localhost:9999/test",
            {"event": "test"},
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_webhook_with_secret(self, httpx_mock):
        """Test webhook with HMAC signature."""
        notifier = Notifier()
        httpx_mock.add_response(url="http://localhost:9999/test", json={"status": "ok"})

        result = await notifier.send_webhook(
            "http://localhost:9999/test",
            {"event": "test"},
            secret="mysecret",
        )
        assert result is True
        # Verify signature header was added
        request = httpx_mock.get_request()
        assert "X-Webhook-Signature" in request.headers


class TestProcessEvent:
    """Tests for event processing."""

    @pytest.mark.asyncio
    async def test_process_event_no_callbacks(self):
        """Test event processing with no callbacks."""
        notifier = Notifier()
        results = await notifier.process_event("test_event")
        assert results == []

    @pytest.mark.asyncio
    async def test_process_event_disabled_callback(self):
        """Test event processing skips disabled callbacks."""
        notifier = Notifier()
        notifier.add_command("echo disabled", enabled=False)
        results = await notifier.process_event("test_event")
        assert results == []


class TestOnTaskComplete:
    """Tests for task completion callbacks."""

    @pytest.mark.asyncio
    async def test_on_task_complete_no_callbacks(self):
        """Test on_task_complete with no callbacks."""
        notifier = Notifier()
        results = await notifier.on_task_complete(
            str(uuid4()), "example.com"
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_on_task_complete_payload(self):
        """Test on_task_complete generates correct payload."""
        notifier = Notifier()
        results = await notifier.on_task_complete(
            str(uuid4()),
            "example.com",
            extra={"finding": "high"},
        )
        assert results == []


class TestFromFile:
    """Tests for loading callbacks from file."""

    def test_from_config_file_not_exists(self, tmp_path: Path):
        """Test loading from non-existent file."""
        config_file = tmp_path / "callbacks.json"
        notifier = Notifier.from_config_file(config_file)
        assert notifier.callbacks == []

    def test_from_config_file_with_data(self, tmp_path: Path):
        """Test loading callbacks from config file."""
        config_file = tmp_path / "callbacks.json"
        config_data = {
            "callbacks": [
                {"command": "echo hello", "enabled": True},
                {"url": "http://localhost:9999", "method": "POST"},
            ]
        }
        config_file.write_text(json.dumps(config_data))
        notifier = Notifier.from_config_file(config_file)
        assert len(notifier.callbacks) == 2
        assert notifier.callbacks[0].command == "echo hello"
        assert notifier.callbacks[1].url == "http://localhost:9999"
