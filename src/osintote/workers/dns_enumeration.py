# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""DNS enumeration stage — dnspython resolver + subdomain discovery.

Uses ``dnspython`` to perform DNS lookups against a target domain:
  - A/AAAA record resolution
  - MX record enumeration
  - NS record enumeration
  - TXT record enumeration (SPF, DKIM, DMARC hints)
  - SOA record for zone info
  - CNAME chain following
  - Optional zone transfer attempt (AXFR)

Example::

    stage = DnsEnumerationStage(domain="example.com")
    result = stage.execute(ctx)
"""

from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass
from typing import Any

import dns.query  # type: ignore[import-untyped]
import dns.rdatatype  # type: ignore[import-untyped]
import dns.resolver  # type: ignore[import-untyped]
import dns.zone  # type: ignore[import-untyped]

from osintote.engine.stage import Stage, StageContext, StageResult, register_stage

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class DnsConfig:
    """Configuration for DNS enumeration."""

    domain: str
    timeout: float = 5.0
    max_retries: int = 3
    try_axfr: bool = False  # Zone transfer (often blocked)
    follow_cname: bool = True

    @property
    def nameservers(self) -> list[str]:
        """Default public DNS servers."""
        return ["8.8.8.8", "8.8.4.4", "1.1.1.1"]


# ── Stage ───────────────────────────────────────────────────────────────────


class DnsEnumerationStage(Stage):
    """DNS enumeration stage using dnspython.

    Performs comprehensive DNS lookups against a target domain including
    A/AAAA, MX, NS, TXT, SOA, and CNAME records. Optionally attempts
    zone transfers (AXFR) for public zone info.

    Parameters
    ----------
    domain:
        Target domain to enumerate.
    timeout:
        DNS query timeout in seconds.
    max_retries:
        Maximum retries per query.
    try_axfr:
        Attempt zone transfer (AXFR) against NS records.
    follow_cname:
        Follow CNAME chains to final targets.
    nameservers:
        Custom DNS servers (default: Google + Cloudflare public).
    """

    name: str = "dns-enumeration"
    cost: str = "light"

    domain: str = ""
    timeout: float = 5.0
    max_retries: int = 3
    try_axfr: bool = False
    follow_cname: bool = True
    nameservers: list[str] = None  # type: ignore[assignment]

    def __init__(
        self,
        *,
        domain: str = "",
        timeout: float = 5.0,
        max_retries: int = 3,
        try_axfr: bool = False,
        follow_cname: bool = True,
        nameservers: list[str] | None = None,
    ) -> None:
        """Initialize DNS enumeration stage."""
        self.domain = domain
        self.timeout = timeout
        self.max_retries = max_retries
        self.try_axfr = try_axfr
        self.follow_cname = follow_cname
        self.nameservers = nameservers or ["8.8.8.8", "8.8.4.4", "1.1.1.1"]

    def execute(self, ctx: StageContext) -> StageResult:
        """Execute DNS enumeration against the target domain.

        Performs A/AAAA, MX, NS, TXT, SOA, CNAME lookups and optional
        zone transfer (AXFR) against the target domain.

        Parameters
        ----------
        ctx:
            Stage context with target information.

        Returns
        -------
        StageResult
            DNS enumeration results including discovered records.
        """
        target = ctx.target_name if not self.domain else self.domain
        records: list[dict[str, Any]] = []
        errors: list[str] = []

        # Build resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout * self.max_retries
        resolver.nameservers = self.nameservers

        try:
            # 1. A records
            a_records = self._query(resolver, target, "A", errors)
            for rdata in a_records:
                records.append(
                    {
                        "type": "dns-a",
                        "target": target,
                        "data": {
                            "record_type": "A",
                            "address": str(rdata),
                            "ttl": int(rdata.ttl),
                        },
                    }
                )

            # 2. AAAA records
            aaaa_records = self._query(resolver, target, "AAAA", errors)
            for rdata in aaaa_records:
                records.append(
                    {
                        "type": "dns-aaaa",
                        "target": target,
                        "data": {
                            "record_type": "AAAA",
                            "address": str(rdata),
                            "ttl": int(rdata.ttl),
                        },
                    }
                )

            # 3. MX records
            mx_records = self._query(resolver, target, "MX", errors)
            for rdata in mx_records:
                records.append(
                    {
                        "type": "dns-mx",
                        "target": target,
                        "data": {
                            "record_type": "MX",
                            "exchange": str(rdata.exchange).rstrip("."),
                            "preference": int(rdata.preference),
                        },
                    }
                )

            # 4. NS records
            ns_records = self._query(resolver, target, "NS", errors)
            for rdata in ns_records:
                records.append(
                    {
                        "type": "dns-ns",
                        "target": target,
                        "data": {
                            "record_type": "NS",
                            "nameserver": str(rdata.target).rstrip("."),
                        },
                    }
                )

            # 5. TXT records
            txt_records = self._query(resolver, target, "TXT", errors)
            for rdata in txt_records:
                txt_str = "".join(str(x) for x in rdata.strings)
                records.append(
                    {
                        "type": "dns-txt",
                        "target": target,
                        "data": {
                            "record_type": "TXT",
                            "value": txt_str,
                        },
                    }
                )

            # 6. SOA record
            try:
                soa_records = resolver.resolve(target, "SOA")
                for rdata in soa_records:
                    records.append(
                        {
                            "type": "dns-soa",
                            "target": target,
                            "data": {
                                "record_type": "SOA",
                                "mname": str(rdata.mname).rstrip("."),
                                "rname": str(rdata.rname).rstrip("."),
                                "serial": int(rdata.serial),
                                "refresh": int(rdata.refresh),
                                "retry": int(rdata.retry),
                                "expire": int(rdata.expire),
                                "minimum": int(rdata.minimum),
                            },
                        }
                    )
            except dns.resolver.NoAnswer:
                pass

            # 7. CNAME chain (if target is not the original domain)
            if self.follow_cname and target != self.domain:
                cname_records = self._query(resolver, target, "CNAME", errors)
                for rdata in cname_records:
                    cname_target = str(rdata.target).rstrip(".")
                    records.append(
                        {
                            "type": "dns-cname",
                            "target": target,
                            "data": {
                                "record_type": "CNAME",
                                "canonical": cname_target,
                            },
                        }
                    )

            # 8. Optional AXFR (zone transfer)
            if self.try_axfr and ns_records:
                records.extend(self._try_axfr(resolver, target, ns_records))

        except Exception as exc:
            errors.append(f"DNS enumeration failed: {exc}")
            return StageResult.failure(
                error=str(exc),
                message=f"DNS enumeration failed for {target}: {exc}",
            )

        return StageResult.success_result(
            data=records,
            records_count=len(records),
            message=f"Discovered {len(records)} DNS records",
            metadata={"errors": errors if errors else None},
        )

    def _query(
        self,
        resolver: Any,
        domain: str,
        record_type: str,
        errors: list[str],
    ) -> Any:
        """Query DNS records with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return resolver.resolve(domain, record_type)
            except Exception as exc:
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    errors.append(f"{record_type} query failed: {exc}")
                    return []
        return []

    def _try_axfr(
        self,
        resolver: Any,
        target: str,
        ns_records: Any,
    ) -> list[dict[str, Any]]:
        """Attempt zone transfer (AXFR) against NS records."""
        records: list[dict[str, Any]] = []
        ns_targets = [str(r.target).rstrip(".") for r in ns_records[:3]]  # Limit to 3 NS

        for ns in ns_targets:
            try:
                logger.info("Attempting AXFR against %s for %s", ns, target)
                zone = dns.zone.from_xfr(
                    dns.query.xfr(ns, target, timeout=self.timeout),
                )
                for name, ttl, rd in zone.iterate_rdatas():
                    records.append(
                        {
                            "type": "dns-axfr",
                            "target": target,
                            "data": {
                                "record_type": str(rd.rdtype),
                                "name": str(name),
                                "ttl": int(ttl),
                                "value": str(rd),
                            },
                        }
                    )
                logger.info("AXFR successful against %s: %d records", ns, len(records))
                break  # First successful AXFR is enough
            except Exception as exc:
                logger.debug("AXFR failed against %s: %s", ns, exc)

        return records


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    with contextlib.suppress(ImportError):
        register_stage(DnsEnumerationStage)


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run DNS enumeration from CLI."""
    import sys
    import uuid

    from osintote.engine.stage import register_stage

    register_stage(DnsEnumerationStage)

    if len(sys.argv) < 2:
        print("Usage: python -m osintote.workers.dns_enumeration <domain>")
        sys.exit(1)

    domain = sys.argv[1]
    config = DnsConfig(domain=domain)
    stage = DnsEnumerationStage(domain=config.domain)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=domain)

    result = stage.execute(ctx)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.data:
        print(f"Records: {len(result.data)}")
        for rec in result.data[:5]:
            print(f"  - {rec['type']}: {rec['data']}")


if __name__ == "__main__":
    main()
