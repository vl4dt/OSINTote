# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Per-source rate limiter with adaptive backoff.

Provides :class:`RateLimiter` which uses an ``asyncio.Semaphore`` for
concurrency control and automatically halves the rate on 429 responses
before exponentially recovering.  Each limiter is keyed by ``(source,
key_id)`` so that multiple API keys for the same source can share or
isolate rate limits.

Example::

    limiter = RateLimiter(rate=4, burst=2)  # 4 req/s, max 2 concurrent
    async with limiter:
        response = await http_client.get(url)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Rate Limiter ────────────────────────────────────────────────────────────


class RateLimiter:
    """Per-source async rate limiter with adaptive backoff.

    Parameters
    ----------
    rate :
        Requests per second (smoothed).
    burst :
        Maximum concurrent requests allowed.
    retry_on_429 :
        Whether to apply backoff on HTTP 429 responses.
    min_delay :
        Minimum delay in seconds between requests (fallback).
    recovery_factor :
        Multiplier applied to delay when halving on 429.
    max_delay :
        Maximum delay in seconds before exponential recovery kicks in.
    """

    def __init__(
        self,
        *,
        rate: float = 1.0,
        burst: int = 1,
        retry_on_429: bool = True,
        min_delay: float = 0.25,
        recovery_factor: float = 2.0,
        max_delay: float = 60.0,
    ) -> None:
        self.rate = rate
        self.burst = burst
        self.retry_on_429 = retry_on_429
        self.min_delay = min_delay
        self.recovery_factor = recovery_factor
        self.max_delay = max_delay

        self._semaphore = asyncio.Semaphore(burst)
        self._token_bucket: float = rate  # tokens per second
        self._last_request_time: float = 0.0
        self._current_delay: float = 1.0 / max(rate, 0.01)  # seconds between requests
        self._lock = asyncio.Lock()
        self._stats: dict[str, Any] = {
            "total_requests": 0,
            "throttled_requests": 0,
            "backoff_count": 0,
            "recovery_count": 0,
        }

    @property
    def stats(self) -> dict[str, Any]:
        """Current limiter statistics."""
        return dict(self._stats)

    async def __aenter__(self) -> RateLimiter:
        """Acquire semaphore and apply rate limit."""
        await self._semaphore.acquire()
        self._stats["total_requests"] += 1
        await self._wait()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Release semaphore."""
        self._semaphore.release()

    async def _wait(self) -> None:
        """Wait until it is safe to send the next request."""
        async with self._lock:
            if self._current_delay > self.min_delay:
                elapsed = time.monotonic() - self._last_request_time
                sleep_time = self._current_delay - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            self._last_request_time = time.monotonic()

    def on_429(self) -> None:
        """Handle a 429 Too Many Requests response — apply backoff."""
        if not self.retry_on_429:
            return
        self._current_delay = min(
            self._current_delay * self.recovery_factor,
            self.max_delay,
        )
        self._stats["backoff_count"] += 1
        self._stats["throttled_requests"] += 1
        logger.warning(
            "Rate limited by %s — backoff to %.2fs",
            self.__class__.__name__,
            self._current_delay,
        )

    def on_success(self) -> None:
        """Handle a successful response — begin exponential recovery."""
        if self._current_delay > self.min_delay * 2:
            self._current_delay = max(
                self._current_delay / self.recovery_factor,
                self.min_delay,
            )
            self._stats["recovery_count"] += 1

    def reset(self) -> None:
        """Reset backoff state to defaults."""
        self._current_delay = 1.0 / max(self.rate, 0.01)
        self._stats["backoff_count"] = 0
        self._stats["throttled_requests"] = 0
        self._stats["recovery_count"] = 0


# ── Rate Limiter Registry ───────────────────────────────────────────────────


@dataclass(frozen=True)
class RateLimiterKey:
    """Immutable key for rate limiter lookup."""

    source: str
    key_id: str | None = None  # per-key rate limiting

    @property
    def label(self) -> str:
        """Human-readable label."""
        if self.key_id:
            return f"{self.source}/{self.key_id}"
        return self.source


class RateLimiterRegistry:
    """Registry for per-source / per-key rate limiters.

    Usage::

        registry = RateLimiterRegistry()
        limiter = registry.get("virustotal", key_id="primary")
        async with limiter:
            ...
    """

    def __init__(self) -> None:
        self._limiters: dict[RateLimiterKey, RateLimiter] = {}

    def get(self, source: str, *, key_id: str | None = None) -> RateLimiter:
        """Get or create a rate limiter for the given source/key."""
        key = RateLimiterKey(source, key_id)
        if key not in self._limiters:
            self._limiters[key] = RateLimiter()
        return self._limiters[key]

    def configure(self, source: str, *, key_id: str | None = None, **kwargs: Any) -> RateLimiter:
        """Configure rate limiter settings for a source/key."""
        key = RateLimiterKey(source, key_id)
        limiter = self._limiters.get(key)
        if limiter is None:
            limiter = RateLimiter(**kwargs)
            self._limiters[key] = limiter
        for attr, value in kwargs.items():
            if hasattr(limiter, attr):
                setattr(limiter, attr, value)
        return limiter

    def reset(self, source: str, *, key_id: str | None = None) -> None:
        """Reset backoff for a source/key."""
        key = RateLimiterKey(source, key_id)
        if key in self._limiters:
            self._limiters[key].reset()

    def all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all registered limiters."""
        return {k.label: v.stats for k, v in self._limiters.items()}


# Global registry instance
DEFAULT_REGISTRY = RateLimiterRegistry()
