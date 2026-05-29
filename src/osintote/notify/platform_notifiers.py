# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Cross-platform desktop notifications for OSINTote."""

from __future__ import annotations

import asyncio
import logging
import platform
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NotificationRequest:
    """A desktop notification request."""

    title: str
    message: str
    category: str = "info"


class PlatformNotifier:
    """Cross-platform desktop notification system.

    Supports:
    - macOS: osascript (AppleScript)
    - Linux: notify-send (libnotify)
    - Windows: toast notifications via PowerShell
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize the platform notifier."""
        self.enabled = enabled
        self._platform = platform.system()

    @property
    def platform(self) -> str:
        """Return the detected platform name."""
        return self._platform

    def _send_macos(self, request: NotificationRequest) -> bool:
        """Send notification via AppleScript (macOS)."""
        script = f'''
        display notification "{request.message}"
        with title "{request.title}"
        '''
        try:
            subprocess.run(
                ["osascript", "-e", script.strip()],
                capture_output=True,
                check=True,
                timeout=5,
            )
            logger.info("macOS notification sent: %s", request.title)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("macOS notification failed: %s", exc)
            return False

    def _send_linux(self, request: NotificationRequest) -> bool:
        """Send notification via notify-send (Linux)."""
        urgency_map = {
            "info": "low",
            "warning": "normal",
            "error": "critical",
            "critical": "critical",
        }
        urgency = urgency_map.get(request.category, "normal")
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, request.title, request.message],
                capture_output=True,
                check=True,
                timeout=5,
            )
            logger.info("Linux notification sent: %s", request.title)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("Linux notification failed: %s", exc)
            return False

    def _send_windows(self, request: NotificationRequest) -> bool:
        """Send notification via PowerShell toast (Windows)."""
        # Simplified toast notification using PowerShell
        # Creates a toast notification that appears in the action center
        script = f'''
        [Windows.UI.Notifications.ToastNotificationManager,
         Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument,
         Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
        $template = @"
        <toast>
            <visual>
                <binding template="ToastGeneric">
                    <text>{request.title}</text>
                    <text>{request.message}</text>
                </binding>
            </visual>
        </toast>
        "@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("OSINTote").Show($toast)
        '''
        try:
            subprocess.run(
                ["powershell", "-Command", script.strip()],
                capture_output=True,
                check=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            logger.info("Windows notification sent: %s", request.title)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("Windows notification failed: %s", exc)
            return False

    def send(self, request: NotificationRequest) -> bool:
        """Send a desktop notification on the current platform.

        Args:
            request: Notification content

        Returns:
            True if notification was sent successfully
        """
        if not self.enabled:
            logger.debug("Notifications disabled, skipping: %s", request.title)
            return False

        platform_name = self.platform.lower()

        if platform_name == "darwin":
            return self._send_macos(request)
        elif platform_name == "linux":
            return self._send_linux(request)
        elif platform_name == "windows":
            return self._send_windows(request)
        else:
            logger.warning("Unknown platform %s, cannot send desktop notification", self.platform)
            return False

    async def send_async(self, request: NotificationRequest) -> bool:
        """Send a desktop notification asynchronously."""
        return await asyncio.to_thread(self.send, request)
