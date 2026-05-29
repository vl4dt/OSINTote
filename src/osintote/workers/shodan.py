# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Shodan API source — network reconnaissance via Shodan.

Performs Shodan API queries for:
  - Host information (IP lookup)
  - Port/service discovery
  - Banner grab information
  - Vulnerability data
  - Organization/ISP info
  - Location data

Uses httpx for API calls with built-in rate limiting
(1 request/second for free tier).

Example::

    from osintote.workers.shodan import ShodanStage

    stage = ShodanStage(
        api_key="shodan_api_key_here",
        ip="93.184.216.34",
    )
    result = stage.execute(ctx)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx  # type: ignore[import-untyped]

from osintote.engine.rate_limiter import RateLimiter, RateLimiterRegistry
from osintote.engine.stage import Stage, StageContext, StageResult, register_stage

logger = logging.getLogger(__name__)

API_BASE = "https://api.shodan.io"

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class ShodanConfig:
    """Configuration for Shodan API."""

    api_key: str
    ip: str = ""
    domain: str = ""
    query: str = ""
    max_results: int = 100
    retry_delay: float = 1.0  # 1 req/s for free tier


# ── Stage ───────────────────────────────────────────────────────────────────


class ShodanStage(Stage):
    """Shodan API stage — network reconnaissance.

    Performs host information queries, port/service discovery,
    and banner grab analysis via the Shodan API.

    Parameters
    ----------
    api_key:
        Shodan API key (required).
    ip:
        Target IP address to look up.
    domain:
        Target domain to look up (resolved to IP).
    query:
        Optional Shodan query string.
    max_results:
        Maximum number of results to return.
    retry_delay:
        Delay between API requests (seconds).
    """

    name: str = "shodan"
    cost: str = "medium"

    api_key: str = ""
    ip: str = ""
    domain: str = ""
    query: str = ""
    max_results: int = 100
    retry_delay: float = 1.0

    def __init__(
        self,
        *,
        api_key: str = "",
        ip: str = "",
        domain: str = "",
        query: str = "",
        max_results: int = 100,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize Shodan stage."""
        self.api_key = api_key
        self.ip = ip
        self.domain = domain
        self.query = query
        self.max_results = max_results
        self.retry_delay = retry_delay

    def execute(self, ctx: StageContext) -> StageResult:
        """Execute Shodan lookup against the target.

        Performs host information queries and port/service
        discovery via the Shodan API.

        Parameters
        ----------
        ctx:
            Stage context with target information.

        Returns
        -------
        StageResult
            Shodan analysis results.
        """
        if not self.api_key:
            return StageResult.failure(
                error="Shodan API key not configured",
                message="Shodan API key required",
            )

        # Determine target
        target = ctx.target_name
        ip = self.ip or self.domain or target

        records: list[dict[str, Any]] = []
        errors: list[str] = []

        import asyncio

        # Create rate limiter for Shodan (1 req/s free tier)
        limiter = RateLimiterRegistry().configure("shodan", rate=1, burst=1)

        async def _run() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Host lookup (IP)
                if self.ip:
                    host_data = await self._get_host(client, ip, limiter)
                    if host_data:
                        records.extend(self._parse_host(host_data, ip))

                # 2. Domain lookup (resolve + host)
                elif self.domain:
                    host_data = await self._get_host(client, self.domain, limiter)
                    if host_data:
                        records.extend(self._parse_host(host_data, self.domain))

                # 3. Search query
                if self.query:
                    search_results = await self._search(client, self.query, limiter)
                    records.extend(search_results)

                # 4. Fallback: try target as IP/domain
                elif not records:
                    host_data = await self._get_host(client, target, limiter)
                    if host_data:
                        records.extend(self._parse_host(host_data, target))

            return records

        try:
            records = asyncio.run(_run())
        except Exception as exc:
            errors.append(f"Shodan API error: {exc}")
            return StageResult.failure(
                error=str(exc),
                message=f"Shodan lookup failed: {exc}",
            )

        return StageResult.success_result(
            data=records,
            records_count=len(records),
            message=f"Retrieved {len(records)} Shodan records",
            metadata={"errors": errors if errors else None},
        )

    async def _get_host(
        self,
        client: httpx.AsyncClient,
        target: str,
        limiter: RateLimiter,
    ) -> dict[str, Any] | None:
        """Get host information from Shodan."""
        try:
            async with limiter:
                resp = await client.get(
                    f"{API_BASE}/shodan/host/{target}",
                    params={"key": self.api_key},
                )

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                logger.info("Shodan host not found: %s", target)
                return None
            elif resp.status_code == 401:
                logger.error("Shodan API key invalid")
                return None
            else:
                logger.warning("Shodan host lookup failed: %d", resp.status_code)
                return None
        except Exception as exc:
            logger.error("Failed to get host info for %s: %s", target, exc)
            return None

    async def _search(
        self,
        client: httpx.AsyncClient,
        query: str,
        limiter: RateLimiter,
    ) -> list[dict[str, Any]]:
        """Search Shodan with a query string."""
        records: list[dict[str, Any]] = []

        try:
            async with limiter:
                resp = await client.get(
                    f"{API_BASE}/shodan/host/search",
                    params={
                        "query": query,
                        "key": self.api_key,
                        "max_results": min(self.max_results, 1000),
                    },
                )

            if resp.status_code == 200:
                data = resp.json()
                count = data.get("total", 0)
                for host in data.get("matches", [])[: self.max_results]:
                    records.append(
                        {
                            "type": "shodan-search",
                            "target": query,
                            "data": {
                                "record_type": "ShodanSearch",
                                "ip": host.get("ip", ""),
                                "port": host.get("port"),
                                "org": host.get("org", ""),
                                "hostnames": host.get("hostnames", []),
                                "country": host.get("country_name", ""),
                            },
                        }
                    )
                logger.info(
                    "Shodan search '%s': %d results (total: %d)", query, len(records), count
                )
            else:
                logger.warning("Shodan search failed: %d", resp.status_code)
        except Exception as exc:
            logger.error("Shodan search failed: %s", exc)

        return records

    @staticmethod
    def _parse_host(host_data: dict[str, Any], target: str) -> list[dict[str, Any]]:
        """Parse Shodan host data into structured records."""
        records: list[dict[str, Any]] = []

        # Main host info
        ports = host_data.get("ports", [])
        vulns = host_data.get("vulns", [])

        # Host summary
        records.append(
            {
                "type": "shodan-host",
                "target": target,
                "data": {
                    "record_type": "ShodanHost",
                    "ip": host_data.get("ip", ""),
                    "hostname": host_data.get("hostname", ""),
                    "org": host_data.get("org", ""),
                    "country": host_data.get("country_name", ""),
                    "city": host_data.get("city", ""),
                    "os": host_data.get("os", ""),
                    "ports": ports,
                    "vulns": [v for v in vulns],
                    "last_update": host_data.get("last_update", ""),
                },
            }
        )

        # Per-port service info
        for port_info in host_data.get("data", []):
            port = port_info.get("port")
            if port not in ports:
                continue

            records.append(
                {
                    "type": "shodan-service",
                    "target": target,
                    "data": {
                        "record_type": "ShodanService",
                        "port": port,
                        "product": port_info.get("product", ""),
                        "version": port_info.get("version", ""),
                        "banner": port_info.get("data", "")[:500],
                        "cpe": port_info.get("cpe", ""),
                    },
                }
            )

        # Vulnerabilities
        for vuln in vulns:
            records.append(
                {
                    "type": "shodan-vuln",
                    "target": target,
                    "data": {
                        "record_type": "ShodanVuln",
                        "vulnerability": vuln,
                        "severity": "critical",
                    },
                }
            )

        return records


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    try:
        from osintote.engine.stage import register_stage

        register_stage(ShodanStage)
    except ImportError:
        pass


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run Shodan lookup from CLI."""
    import sys
    import uuid

    register_stage(ShodanStage)

    if len(sys.argv) < 3:
        print("Usage: python -m osintote.workers.shodan <api_key> <ip_or_domain>")
        sys.exit(1)

    api_key = sys.argv[1]
    target = sys.argv[2]

    stage = ShodanStage(api_key=api_key, ip=target)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=target)

    result = stage.execute(ctx)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.data:
        print(f"Records: {len(result.data)}")


if __name__ == "__main__":
    main()
