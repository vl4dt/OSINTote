# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Notification and callback system for OSINTote."""

from __future__ import annotations

from osintote.notify.notifier import Notifier
from osintote.notify.platform_notifiers import PlatformNotifier

__all__: list[str] = ["Notifier", "PlatformNotifier"]
