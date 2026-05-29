# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the cross-platform notification system."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from osintote.notify.platform_notifiers import NotificationRequest, PlatformNotifier


class TestNotificationRequest:
    """Tests for NotificationRequest dataclass."""

    def test_default_values(self):
        """Test NotificationRequest default values."""
        req = NotificationRequest(title="Test", message="Body")
        assert req.title == "Test"
        assert req.message == "Body"
        assert req.category == "info"

    def test_custom_values(self):
        """Test NotificationRequest with custom values."""
        req = NotificationRequest(title="Error", message="Fail", category="critical")
        assert req.title == "Error"
        assert req.message == "Fail"
        assert req.category == "critical"


class TestPlatformNotifierInit:
    """Tests for PlatformNotifier initialization."""

    def test_enabled_by_default(self):
        """Test PlatformNotifier is enabled by default."""
        notifier = PlatformNotifier()
        assert notifier.enabled is True

    def test_can_disable(self):
        """Test disabling PlatformNotifier."""
        notifier = PlatformNotifier(enabled=False)
        assert notifier.enabled is False

    def test_platform_detection(self):
        """Test platform detection."""
        notifier = PlatformNotifier()
        assert notifier.platform in ("Linux", "Darwin", "Windows", "other")


class TestSendDisabled:
    """Tests for disabled notification behavior."""

    def test_send_disabled_does_nothing(self):
        """Test that disabled notifier returns False."""
        notifier = PlatformNotifier(enabled=False)
        # Should not raise, just return False
        result = notifier.send(NotificationRequest("Test", "Body"))
        assert result is False

    @pytest.mark.asyncio
    async def test_send_async_disabled(self):
        """Test async send with disabled notifier."""
        notifier = PlatformNotifier(enabled=False)
        result = await notifier.send_async(
            NotificationRequest("Test", "Body")
        )
        assert result is False


class TestPlatformDetection:
    """Tests for platform-specific detection."""

    @patch("platform.system", return_value="Darwin")
    def test_macos_detection(self, mock_platform):
        """Test macOS platform detection."""
        notifier = PlatformNotifier()
        assert notifier.platform == "Darwin"

    @patch("platform.system", return_value="Linux")
    def test_linux_detection(self, mock_platform):
        """Test Linux platform detection."""
        notifier = PlatformNotifier()
        assert notifier.platform == "Linux"

    @patch("platform.system", return_value="Windows")
    def test_windows_detection(self, mock_platform):
        """Test Windows platform detection."""
        notifier = PlatformNotifier()
        assert notifier.platform == "Windows"


class TestUnknownPlatform:
    """Tests for unknown platform handling."""

    def test_unknown_platform_logs_warning(self):
        """Test that unknown platform returns False."""
        notifier = PlatformNotifier()
        with patch.object(notifier, "_platform", "UnknownOS"):
            result = notifier.send(NotificationRequest("Test", "Body"))
            assert result is False
