# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""subfinder wrapper — subdomain enumeration stage.

Uses the CLI wrapper framework to execute ``subfinder`` safely with
``asyncio.create_subprocess_exec``.  Parses stdout for discovered
subdomains and normalises results to :class:`osintote.models.orm.Record`
dicts.

Example::

    stage = SubfinderStage(domain="example.com")
    records = await stage.execute(ctx, executor)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from osintote.cli.wrapper import SubprocessRunner
from osintote.engine.stage import StageContext, StageResult

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class SubfinderConfig:
    """Configuration for subfinder."""

    domain: str
    sources: str = ""  # comma-separated source list
    timeout: float = 120.0
    max_retries: int = 3
    quiet: bool = True
    extra_args: list[str] = field(default_factory=list)

    @property
    def full_args(self) -> list[str]:
        """All subfinder CLI arguments."""
        args = ["subfinder", "-d", self.domain]
        if self.sources:
            args.extend(["-sources", self.sources])
        if self.quiet:
            args.append("-q")
        args.extend(self.extra_args)
        return args


# ── Stage ───────────────────────────────────────────────────────────────────


class SubfinderStage:
    """subfinder subdomain enumeration stage.

    Executes ``subfinder`` via :class:`osintote.cli.wrapper.SubprocessRunner`,
    parses stdout for discovered subdomains, and produces
    :class:`StageResult` records.
    """

    NAME = "subfinder"

    def __init__(self, config: SubfinderConfig) -> None:
        self.config = config
        self.runner = SubprocessRunner()

    async def execute(
        self, ctx: StageContext, executor: Any
    ) -> StageResult:
        """Run subfinder and return normalised records."""
        try:
            result = await self.runner.run_safe(
                *self.config.full_args,
                timeout=self.config.timeout,
            )

            if not result.success:
                return StageResult.failure(
                    error=result.stderr.strip() or "subfinder command failed",
                    message=result.stderr.strip() or "subfinder command failed",
                )

            subdomains = self._parse_output(result.stdout)
            subdomains = self._dedup(subdomains)

            records = [
                {
                    "id": str(__import__("uuid", fromlist=["uuid4"]).uuid4()),
                    "type": "dns",
                    "target": self.config.domain,
                    "data": {"subdomain": sd, "source": "subfinder"},
                }
                for sd in subdomains
            ]

            return StageResult.success_result(
                data=records,
                records_count=len(records),
                message=f"Discovered {len(subdomains)} subdomains",
            )

        except Exception as exc:
            return StageResult.failure(
                error=str(exc),
                message=str(exc),
            )

    @staticmethod
    def _parse_output(output: str) -> list[str]:
        """Parse subfinder stdout for subdomain names."""
        subdomains: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            line = line.rstrip(".")
            subdomains.append(line)
        return subdomains

    @staticmethod
    def _dedup(subdomains: list[str]) -> list[str]:
        """Deduplicate subdomains preserving order."""
        seen: set[str] = set()
        result: list[str] = []
        for sd in subdomains:
            lower = sd.lower()
            if lower and lower not in seen:
                seen.add(lower)
                result.append(lower)
        return result


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    from osintote.engine.stage import STAGE_REGISTRY

    if SubfinderStage.NAME not in STAGE_REGISTRY:
        STAGE_REGISTRY[SubfinderStage.NAME] = SubfinderStage


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run subfinder scan from CLI."""
    import asyncio
    import sys
    import uuid

    if len(sys.argv) < 2:
        print("Usage: python -m osintote.workers.subfinder <domain>")
        sys.exit(1)

    domain = sys.argv[1]
    config = SubfinderConfig(domain=domain)
    stage = SubfinderStage(config)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=domain)

    async def _run() -> None:
        result = await stage.execute(ctx, None)
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        if result.data:
            print(f"Records: {len(result.data)}")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
