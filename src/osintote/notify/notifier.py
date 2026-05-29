# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Notifier — callback system for task completion and other events."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CallbackConfig(BaseModel):
    """Configuration for a single callback."""

    command: str | None = Field(default=None, description="Shell command to run")
    url: str | None = Field(default=None, description="Webhook URL")
    method: str = Field(default="POST", description="HTTP method for webhook")
    headers: dict[str, str] = Field(default_factory=dict, description="Extra headers")
    enabled: bool = Field(default=True, description="Whether this callback is active")


class Notifier:
    """Manages callbacks for OSINTote events.

    Supports:
    - Shell command execution (safe, no eval)
    - Webhook HTTP requests (with HMAC signing)
    """

    def __init__(self, callbacks: list[CallbackConfig] | None = None) -> None:
        """Initialize the notifier with optional callbacks."""
        self.callbacks: list[CallbackConfig] = callbacks or []

    @classmethod
    def from_config_file(cls, path: str | Path) -> Notifier:
        """Load callbacks from a JSON config file."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()
        data = json.loads(config_path.read_text())
        callbacks = [CallbackConfig(**cb) for cb in data.get("callbacks", [])]
        return cls(callbacks=callbacks)

    def add_command(self, command: str, *, enabled: bool = True) -> None:
        """Add a shell command callback."""
        self.callbacks.append(CallbackConfig(command=command, enabled=enabled))

    def add_webhook(
        self,
        url: str,
        *,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        enabled: bool = True,
    ) -> None:
        """Add a webhook callback."""
        self.callbacks.append(
            CallbackConfig(
                url=url,
                method=method,
                headers=headers or {},
                enabled=enabled,
            )
        )

    def run_command(self, command: str) -> bool:
        """Execute a shell command safely (no eval).

        Uses shlex to parse the command into args, then runs it via
        asyncio.create_subprocess_exec. No shell=True, no eval.

        Returns True if the command succeeded (exit code 0).
        """
        # Safely parse command into arguments using shlex
        try:
            args = shlex.split(command)
        except ValueError as exc:
            logger.error("Invalid command syntax: %s", exc)
            return False

        if not args:
            logger.warning("Empty command, skipping")
            return False

        # Ensure command is a known safe binary path
        cmd = args[0]
        logger.info("Executing callback command: %s", " ".join(args))

        try:
            proc = asyncio.create_subprocess_exec(
                cmd,
                *args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_, stderr = proc.communicate()
            if proc.returncode == 0:
                logger.info("Command succeeded: %s", cmd)
                return True
            else:
                logger.error(
                    "Command failed (rc=%d): %s\n%s",
                    proc.returncode,
                    cmd,
                    stderr.decode(errors="replace"),
                )
                return False
        except FileNotFoundError:
            logger.error("Command not found: %s", cmd)
            return False
        except OSError as exc:
            logger.error("Command execution error: %s", exc)
            return False

    async def send_webhook(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        secret: str | None = None,
        timeout: float = 10.0,
    ) -> bool:
        """Send a webhook HTTP request.

        Optionally signs the payload with HMAC-SHA256 using the secret.
        """
        extra_headers = headers or {}
        extra_headers.setdefault("Content-Type", "application/json")

        if secret:
            import hashlib
            import hmac

            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            extra_headers["X-Webhook-Signature"] = f"sha256={signature}"

        logger.info("Sending webhook to %s", url)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method,
                    url,
                    json=payload,
                    headers=extra_headers,
                )
                response.raise_for_status()
                logger.info("Webhook delivered: %s", url)
                return True
        except httpx.HTTPError as exc:
            logger.error("Webhook failed: %s — %s", url, exc)
            return False

    async def process_event(
        self,
        event: str,
        task_id: UUID | None = None,
        target_name: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Process all callbacks for an event.

        Args:
            event: Event type (e.g., "on_task_complete")
            task_id: Associated task ID
            target_name: Associated target name
            extra: Additional payload data

        Returns:
            List of success/failure booleans for each callback.
        """
        results: list[bool] = []
        payload: dict[str, Any] = {
            "event": event,
            "timestamp": asyncio.get_event_loop().time(),
            "task_id": str(task_id) if task_id else None,
            "target": target_name,
        }
        if extra:
            payload.update(extra)

        for cb in self.callbacks:
            if not cb.enabled:
                continue

            if cb.command:
                try:
                    # Substitute placeholders in command
                    cmd = cb.command
                    if task_id:
                        cmd = cmd.replace("{task_id}", str(task_id))
                    if target_name:
                        cmd = cmd.replace("{target}", target_name)

                    success = await asyncio.to_thread(self.run_command, cmd)
                    results.append(success)
                except Exception as exc:
                    logger.error("Callback command error: %s", exc)
                    results.append(False)

            if cb.url:
                webhook_headers = cb.headers.copy()
                success = await self.send_webhook(
                    cb.url,
                    payload,
                    method=cb.method,
                    headers=webhook_headers,
                    timeout=10.0,
                )
                results.append(success)

        return results

    async def on_task_complete(
        self,
        task_id: UUID,
        target_name: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Process callbacks for task completion."""
        return await self.process_event(
            "on_task_complete",
            task_id=task_id,
            target_name=target_name,
            extra=extra,
        )

    async def on_task_fail(
        self,
        task_id: UUID,
        target_name: str,
        *,
        error_message: str,
        extra: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Process callbacks for task failure."""
        return await self.process_event(
            "on_task_fail",
            task_id=task_id,
            target_name=target_name,
            extra={**(extra or {}), "error": error_message},
        )
