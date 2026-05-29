# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""WHOIS stage — python-whois wrapper, domain registration info.

Parses WHOIS responses to extract domain registration details:
  - Registrar information
  - Registration/expiry dates
  - Name servers
  - Domain status
  - Registrant contact (if available)

Example::

    stage = WhoisStage(domain="example.com")
    result = stage.execute(ctx)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import whois  # type: ignore[import-untyped]

from osintote.engine.stage import Stage, StageContext, StageResult, register_stage

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class WhoisConfig:
    """Configuration for WHOIS lookup."""

    domain: str
    timeout: float = 10.0
    max_retries: int = 3


# ── Stage ───────────────────────────────────────────────────────────────────


class WhoisStage(Stage):
    """WHOIS lookup stage using python-whois.

    Performs WHOIS queries against a target domain and extracts
    registration details including registrar, dates, name servers,
    and domain status.

    Parameters
    ----------
    domain:
        Target domain to query.
    timeout:
        WHOIS query timeout in seconds.
    max_retries:
        Maximum retries per query.
    """

    name: str = "whois"
    cost: str = "light"

    domain: str = ""
    timeout: float = 10.0
    max_retries: int = 3

    def __init__(
        self,
        *,
        domain: str = "",
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize WHOIS stage."""
        self.domain = domain
        self.timeout = timeout
        self.max_retries = max_retries

    def execute(self, ctx: StageContext) -> StageResult:
        """Execute WHOIS lookup against the target domain.

        Performs WHOIS query and extracts domain registration details.

        Parameters
        ----------
        ctx:
            Stage context with target information.

        Returns
        -------
        StageResult
            WHOIS lookup results.
        """
        target = ctx.target_name if not self.domain else self.domain
        errors: list[str] = []

        for attempt in range(self.max_retries):
            try:
                domain_info = whois.whois(target)
                record = self._parse_whois(domain_info, target)
                return StageResult.success_result(
                    data=record,
                    records_count=1,
                    message=f"WHOIS info retrieved for {target}",
                )
            except Exception as exc:
                if attempt < self.max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))
                else:
                    errors.append(f"WHOIS query failed: {exc}")
                    return StageResult.failure(
                        error=str(exc),
                        message=f"WHOIS lookup failed for {target}: {exc}",
                    )

        return StageResult.failure(
            error="WHOIS query exhausted retries",
            message=f"WHOIS lookup failed for {target}",
        )

    @staticmethod
    def _parse_whois(whois_data: Any, target: str) -> dict[str, Any]:
        """Parse WHOIS response into a structured record.

        Parameters
        ----------
        whois_data:
            Raw WHOIS response from python-whois.
        target:
            Target domain name.

        Returns
        -------
        dict[str, Any]
            Structured WHOIS data.
        """
        record: dict[str, Any] = {
            "type": "whois",
            "target": target,
            "data": {
                "record_type": "WHOIS",
            },
        }

        # Extract common fields
        fields_to_extract = [
            ("domain_name", "domain"),
            ("registrar", "registrar"),
            ("creation_date", "created"),
            ("expiration_date", "expires"),
            ("updated_date", "updated"),
            ("name_servers", "name_servers"),
            ("status", "status"),
            ("registrant_name", "registrant_name"),
            ("registrant_email", "registrant_email"),
            ("registrant_country", "registrant_country"),
        ]

        for key, out_key in fields_to_extract:
            value = getattr(whois_data, key, None)
            if value is not None:
                # Normalize date fields to ISO strings
                if isinstance(value, (list, tuple)):
                    value = [str(v) for v in value]
                elif hasattr(value, "isoformat"):
                    value = value.isoformat()
                else:
                    value = str(value)

                record["data"][out_key] = value

        # Normalize name_servers to list of strings
        ns = record["data"].get("name_servers", [])
        if isinstance(ns, str):
            ns = [ns]
        record["data"]["name_servers"] = ns

        return record


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    try:
        from osintote.engine.stage import register_stage
        register_stage(WhoisStage)
    except ImportError:
        pass


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run WHOIS lookup from CLI."""
    import sys
    import uuid

    from osintote.engine.stage import STAGE_REGISTRY, register_stage

    register_stage(WhoisStage)

    if len(sys.argv) < 2:
        print("Usage: python -m osintote.workers.whois <domain>")
        sys.exit(1)

    domain = sys.argv[1]
    config = WhoisConfig(domain=domain)
    stage = WhoisStage(domain=config.domain)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=domain)

    result = stage.execute(ctx)
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.data:
        print(f"Data: {result.data}")


if __name__ == "__main__":
    main()
