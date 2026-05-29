# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""VirusTotal API source — threat intelligence lookups.

Performs VirusTotal API queries for:
  - Domain reputation analysis
  - URL scanning status
  - DNS resolution history
  - Subdomains list
  - Last analysis results

Uses httpx for API calls with built-in rate limiting
(4 requests/second for free tier).

Example::

    from osintote.workers.virustotal import VirusTotalStage

    stage = VirusTotalStage(
        api_key="vt_api_key_here",
        domain="example.com",
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

API_BASE = "https://www.virustotal.com/api/v3"

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class VirusTotalConfig:
    """Configuration for VirusTotal API."""

    api_key: str
    domain: str = ""
    url: str = ""
    max_results: int = 100
    retry_delay: float = 0.25  # 4 req/s = 250ms between requests


# ── Stage ───────────────────────────────────────────────────────────────────


class VirusTotalStage(Stage):
    """VirusTotal API stage — threat intelligence lookups.

    Performs domain reputation analysis, URL scanning status,
    DNS resolution history, and subdomain enumeration via the
    VirusTotal API.

    Parameters
    ----------
    api_key:
        VirusTotal API key (required).
    domain:
        Target domain to analyze.
    url:
        Optional URL to analyze (overrides domain lookup).
    max_results:
        Maximum number of results to return.
    retry_delay:
        Delay between API requests (seconds).
    """

    name: str = "virustotal"
    cost: str = "light"

    api_key: str = ""
    domain: str = ""
    url: str = ""
    max_results: int = 100
    retry_delay: float = 0.25

    def __init__(
        self,
        *,
        api_key: str = "",
        domain: str = "",
        url: str = "",
        max_results: int = 100,
        retry_delay: float = 0.25,
    ) -> None:
        """Initialize VirusTotal stage."""
        self.api_key = api_key
        self.domain = domain
        self.url = url
        self.max_results = max_results
        self.retry_delay = retry_delay

    def execute(self, ctx: StageContext) -> StageResult:
        """Execute VirusTotal lookup against the target.

        Performs domain reputation analysis and URL scanning
        status queries against the VirusTotal API.

        Parameters
        ----------
        ctx:
            Stage context with target information.

        Returns
        -------
        StageResult
            VirusTotal analysis results.
        """
        if not self.api_key:
            return StageResult.failure(
                error="VirusTotal API key not configured",
                message="VirusTotal API key required",
            )

        target = ctx.target_name if not self.domain else self.domain
        records: list[dict[str, Any]] = []
        errors: list[str] = []

        # Create rate limiter for VirusTotal (4 req/s free tier)
        limiter = RateLimiterRegistry().configure("virustotal", rate=4, burst=2)

        async def _run() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Domain analysis
                if self.domain or not self.url:
                    domain_id = await self._get_domain_id(client, target)
                    if domain_id:
                        results = await self._get_analysis(client, domain_id, limiter)
                        records.extend(results)

                        # 2. DNS resolution history
                        dns_results = await self._get_dns_history(client, domain_id, limiter)
                        records.extend(dns_results)

                        # 3. Subdomains
                        subdomains = await self._get_subdomains(client, domain_id, limiter)
                        records.extend(subdomains)

                # 4. URL analysis (if specified)
                if self.url:
                    url_id = await self._get_url_id(client, self.url)
                    if url_id:
                        results = await self._get_analysis(client, url_id, limiter)
                        records.extend(results)

            return records

        import asyncio

        try:
            records = asyncio.run(_run())
        except Exception as exc:
            errors.append(f"VirusTotal API error: {exc}")
            return StageResult.failure(
                error=str(exc),
                message=f"VirusTotal lookup failed: {exc}",
            )

        return StageResult.success_result(
            data=records,
            records_count=len(records),
            message=f"Retrieved {len(records)} VirusTotal records",
            metadata={"errors": errors if errors else None},
        )

    async def _get_domain_id(self, client: httpx.AsyncClient, domain: str) -> str | None:
        """Get the VirusTotal domain analysis ID."""
        try:
            resp = await client.get(f"{API_BASE}/domains/{domain}")
            if resp.status_code == 200:
                return resp.json()["data"]["id"]
            elif resp.status_code == 404:
                return None
            else:
                logger.warning("VirusTotal domain lookup failed: %d", resp.status_code)
                return None
        except Exception as exc:
            logger.error("Failed to get domain ID for %s: %s", domain, exc)
            return None

    async def _get_url_id(self, client: httpx.AsyncClient, url: str) -> str | None:
        """Get the VirusTotal URL analysis ID."""
        try:
            resp = await client.get(f"{API_BASE}/urls?url={url}")
            if resp.status_code == 200:
                return resp.json()["data"]["id"]
            elif resp.status_code == 404:
                return None
            else:
                logger.warning("VirusTotal URL lookup failed: %d", resp.status_code)
                return None
        except Exception as exc:
            logger.error("Failed to get URL ID: %s", exc)
            return None

    async def _get_analysis(
        self,
        client: httpx.AsyncClient,
        resource_id: str,
        limiter: RateLimiter,
    ) -> list[dict[str, Any]]:
        """Get last analysis results for a resource."""
        records: list[dict[str, Any]] = []

        async with limiter:
            try:
                resp = await client.get(f"{API_BASE}/analyses/{resource_id}")
                if resp.status_code == 200:
                    data = resp.json()["data"]["attributes"]
                    results = data.get("last_analysis_results", {})
                    stats = data.get("last_analysis_stats", {})

                    for label, result in results.items():
                        if result.get("category") in ("malicious", "suspicious"):
                            records.append(
                                {
                                    "type": "virustotal-detection",
                                    "target": data.get("url", resource_id),
                                    "data": {
                                        "record_type": "VirusTotal",
                                        "engine": label,
                                        "category": result["category"],
                                        "result": result.get("result", ""),
                                        "severity": "critical"
                                        if result["category"] == "malicious"
                                        else "warning",
                                    },
                                }
                            )

                    records.append(
                        {
                            "type": "virustotal-stats",
                            "target": resource_id,
                            "data": {
                                "record_type": "VirusTotal",
                                "stats": {
                                    "malicious": stats.get("malicious", 0),
                                    "suspicious": stats.get("suspicious", 0),
                                    "undetected": stats.get("undetected", 0),
                                    "harmless": stats.get("harmless", 0),
                                    "timeout": stats.get("timeout", 0),
                                },
                            },
                        }
                    )
            except Exception as exc:
                logger.error("Failed to get analysis: %s", exc)

        return records

    async def _get_dns_history(
        self,
        client: httpx.AsyncClient,
        domain_id: str,
        limiter: RateLimiter,
    ) -> list[dict[str, Any]]:
        """Get DNS resolution history."""
        records: list[dict[str, Any]] = []

        async with limiter:
            try:
                resp = await client.get(
                    f"{API_BASE}/domains/{domain_id}/resolutions",
                    params={"limit": self.max_results},
                )
                if resp.status_code == 200:
                    for item in resp.json()["data"][: self.max_results]:
                        attrs = item["attributes"]
                        records.append(
                            {
                                "type": "virustotal-dns-resolution",
                                "target": domain_id,
                                "data": {
                                    "record_type": "DNSResolution",
                                    "host_ip": attrs.get("host_ip", ""),
                                    "last_dns_record_type": attrs.get("last_dns_record_type", ""),
                                    "resolution_date": attrs.get("date", ""),
                                },
                            }
                        )
            except Exception as exc:
                logger.error("Failed to get DNS history: %s", exc)

        return records

    async def _get_subdomains(
        self,
        client: httpx.AsyncClient,
        domain_id: str,
        limiter: RateLimiter,
    ) -> list[dict[str, Any]]:
        """Get subdomains list."""
        records: list[dict[str, Any]] = []

        async with limiter:
            try:
                resp = await client.get(
                    f"{API_BASE}/domains/{domain_id}/subdomains", params={"limit": self.max_results}
                )
                if resp.status_code == 200:
                    for item in resp.json()["data"][: self.max_results]:
                        subdomain = item.get("id", "")
                        records.append(
                            {
                                "type": "virustotal-subdomain",
                                "target": domain_id,
                                "data": {
                                    "record_type": "Subdomain",
                                    "subdomain": subdomain,
                                },
                            }
                        )
            except Exception as exc:
                logger.error("Failed to get subdomains: %s", exc)

        return records


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    try:
        from osintote.engine.stage import register_stage

        register_stage(VirusTotalStage)
    except ImportError:
        pass


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run VirusTotal lookup from CLI."""
    import sys
    import uuid

    register_stage(VirusTotalStage)

    if len(sys.argv) < 3:
        print("Usage: python -m osintote.workers.virustotal <api_key> <domain>")
        sys.exit(1)

    api_key = sys.argv[1]
    domain = sys.argv[2]

    stage = VirusTotalStage(api_key=api_key, domain=domain)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=domain)

    result = stage.execute(ctx)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.data:
        print(f"Records: {len(result.data)}")


if __name__ == "__main__":
    main()
