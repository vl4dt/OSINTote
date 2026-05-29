# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""HTTP probing stage — httpx alive host discovery.

Discovers live HTTP hosts by probing URLs with configurable concurrency,
timeout, and status code filtering. Captures response headers and body
metadata for downstream analysis.

Example::

    from osintote.workers.http_probe import HttpProbeStage

    stage = HttpProbeStage(
        timeout=10.0,
        max_concurrent=20,
        status_codes=[200, 301, 302],
    )
    result = stage.execute(context)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from osintote.engine.stage import Stage, StageContext, StageResult, register_stage

logger = logging.getLogger(__name__)


class HttpProbeStage(Stage):
    """HTTP probing stage — alive host discovery with httpx.

    Parameters
    ----------
    timeout:
        Request timeout in seconds.
    max_concurrent:
        Maximum concurrent HTTP connections (for future use).
    status_codes:
        Status codes to consider as "live" (default: [200, 301, 302]).
    paths:
        URL paths to probe (default: [/]).
    follow_redirects:
        Whether to follow HTTP redirects.
    """

    name: str = "http-probe"
    cost: str = "light"

    timeout: float = 10.0
    max_concurrent: int = 20
    status_codes: list[int] = None  # type: ignore[assignment]
    paths: list[str] = None  # type: ignore[assignment]
    follow_redirects: bool = True

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        max_concurrent: int = 20,
        status_codes: list[int] | None = None,
        paths: list[str] | None = None,
        follow_redirects: bool = True,
    ) -> None:
        """Initialize the HTTP probing stage."""
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.status_codes = status_codes or [200, 301, 302]
        self.paths = paths or ["/"]
        self.follow_redirects = follow_redirects

    def execute(self, ctx: StageContext) -> StageResult:
        """Execute HTTP probing against the target.

        Discovers live hosts by probing common paths and captures
        response headers and status codes for each response.

        Parameters
        ----------
        ctx:
            Stage context with target information.

        Returns
        -------
        StageResult
            Probing results including discovered hosts and metadata.
        """
        target = ctx.target_name
        results: list[dict[str, Any]] = []
        alive_hosts: list[str] = []

        # Build URLs to probe
        base_urls = self._build_urls(target)

        for url in base_urls:
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(self.timeout),
                    follow_redirects=self.follow_redirects,
                ) as client:
                    response = client.get(url)
                    status = response.status_code

                    if status in self.status_codes:
                        alive_hosts.append(url)
                        result = {
                            "url": url,
                            "status_code": status,
                            "headers": self._capture_headers(response),
                            "content_type": response.headers.get("content-type", ""),
                            "content_length": len(response.content),
                            "is_alive": True,
                        }
                        results.append(result)
                        logger.info(
                            "HTTP probe: %s → %d (%s)",
                            url,
                            status,
                            "ALIVE",
                        )
                    else:
                        logger.debug(
                            "HTTP probe: %s → %d (filtered)",
                            url,
                            status,
                        )

            except httpx.TimeoutException:
                logger.warning("HTTP probe timeout: %s", url)
                results.append(
                    {
                        "url": url,
                        "status_code": 0,
                        "headers": {},
                        "content_type": "",
                        "content_length": 0,
                        "is_alive": False,
                        "error": "timeout",
                    }
                )
            except httpx.RequestError as exc:
                logger.warning("HTTP probe error: %s — %s", url, exc)
                results.append(
                    {
                        "url": url,
                        "status_code": 0,
                        "headers": {},
                        "content_type": "",
                        "content_length": 0,
                        "is_alive": False,
                        "error": str(exc),
                    }
                )

        ctx.records.extend(results)
        return StageResult(
            success=len(alive_hosts) > 0,
            data={"alive_hosts": alive_hosts, "total_probed": len(base_urls)},
            records_count=len(results),
            message=f"Probed {len(base_urls)} URLs, {len(alive_hosts)} alive",
        )

    def _build_urls(self, target: str) -> list[str]:
        """Build list of URLs to probe from target name/IP."""
        urls = []
        for path in self.paths:
            for scheme in ["http", "https"]:
                if "." in target:
                    urls.append(f"{scheme}://{target}{path}")
                else:
                    # For IPs, path should not include port separator
                    clean_path = path if path != "/" else ""
                    urls.append(f"{scheme}://{target}{clean_path}")
        return urls

    def _capture_headers(self, response: httpx.Response) -> dict[str, str]:
        """Capture relevant response headers."""
        return {
            "content-type": response.headers.get("content-type", ""),
            "server": response.headers.get("server", ""),
            "x-powered-by": response.headers.get("x-powered-by", ""),
            "x-frame-options": response.headers.get("x-frame-options", ""),
            "content-security-policy": response.headers.get("content-security-policy", ""),
            "strict-transport-security": response.headers.get("strict-transport-security", ""),
        }


# Register this stage with the global registry
register_stage(HttpProbeStage)
