# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""nuclei wrapper — vulnerability scanning stage.

Uses the CLI wrapper framework to execute ``nuclei`` safely with
``asyncio.create_subprocess_exec``.  Parses JSONL output for
vulnerability findings and normalises results to
:class:`osintote.models.orm.Record` dicts.

Example::

    stage = NucleiStage(target="https://example.com", severity=["high", "critical"])
    records = await stage.execute(ctx, executor)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from osintote.cli.wrapper import SubprocessRunner
from osintote.engine.stage import StageContext, StageResult

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class NucleiConfig:
    """Configuration for nuclei."""

    target: str
    severity: list[str] = field(
        default_factory=lambda: ["unknown", "info", "low", "medium",
                                "high", "critical"]
    )
    templates: str = ""  # path to template directory
    timeout: float = 300.0
    rate_limit: int = 0  # 0 = no limit
    json_output: bool = True
    extra_args: list[str] = field(default_factory=list)

    @property
    def full_args(self) -> list[str]:
        """All nuclei CLI arguments."""
        args = ["nuclei", "-u", self.target]
        if self.templates:
            args.extend(["-templates", self.templates])
        if self.severity:
            args.extend(["-severity", ",".join(self.severity)])
        if self.json_output:
            args.append("-json")
        if self.rate_limit > 0:
            args.extend(["-rl", str(self.rate_limit)])
        args.extend(self.extra_args)
        return args


# ── Stage ───────────────────────────────────────────────────────────────────


class NucleiStage:
    """nuclei vulnerability scanning stage.

    Executes ``nuclei`` via :class:`osintote.cli.wrapper.SubprocessRunner`,
    parses JSONL output for vulnerability findings, and produces
    :class:`StageResult` records.
    """

    NAME = "nuclei"

    def __init__(self, config: NucleiConfig) -> None:
        self.config = config
        self.runner = SubprocessRunner()

    async def execute(
        self, ctx: StageContext, executor: Any
    ) -> StageResult:
        """Run nuclei and return normalised records."""
        try:
            result = await self.runner.run_safe(
                *self.config.full_args,
                timeout=self.config.timeout,
            )

            if not result.success:
                return StageResult.failure(
                    error=result.stderr.strip() or "nuclei command failed",
                    message=result.stderr.strip() or "nuclei command failed",
                )

            findings = self._parse_jsonl(result.stdout)

            # Normalise to Record dicts
            records = [
                {
                    "id": str(__import__("uuid", fromlist=["uuid4"]).uuid4()),
                    "type": "vulnerability",
                    "target": self.config.target,
                    "data": {
                        "template_id": f.get("templateID", ""),
                        "template_path": f.get("templatePath", ""),
                        "host": f.get("host", ""),
                        "matched_at": f.get("matched-line", ""),
                        "severity": (
                            f.get("info", {}).get("severity", "unknown")
                            if f.get("info")
                            else "unknown"
                        ),
                        "name": (
                            f.get("info", {}).get("name", "")
                            if f.get("info")
                            else ""
                        ),
                        "reference": (
                            f.get("info", {}).get("reference", [])
                            if f.get("info")
                            else []
                        ),
                        "extracted_results": f.get("extracted-results", []),
                        "metadata": f.get("metadata", {}),
                    },
                }
                for f in findings
            ]

            # Count by severity
            severity_counts: dict[str, int] = {}
            for f in findings:
                sev = (
                    f.get("info", {}).get("severity", "unknown")
                    if f.get("info")
                    else "unknown"
                )
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            sev_summary = ", ".join(f"{k}:{v}" for k, v in severity_counts.items())
            return StageResult.success_result(
                data=records,
                records_count=len(records),
                message=f"Found {len(records)} vulnerabilities ({sev_summary})",
                metadata={"severity_counts": severity_counts},
            )

        except Exception as exc:
            return StageResult.failure(
                error=str(exc),
                message=str(exc),
            )

    @staticmethod
    def _parse_jsonl(jsonl_text: str) -> list[dict[str, Any]]:
        """Parse nuclei JSONL output into finding dicts."""
        findings: list[dict[str, Any]] = []
        for line in jsonl_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                finding = json.loads(line)
                findings.append(finding)
            except json.JSONDecodeError:
                continue
        return findings

    @staticmethod
    def extract_cves(finding: dict[str, Any]) -> list[str]:
        """Extract CVE IDs from a nuclei finding.

        Looks for CVE patterns in metadata and extracted results.
        """
        cves: list[str] = []
        metadata = finding.get("metadata", {})
        extracted = finding.get("extracted-results", [])

        # Check metadata for CVE IDs
        for _key, val in metadata.items():
            if isinstance(val, str):
                cve_matches = re.findall(r"CVE-\d{4}-\d{4,}", val)
                cves.extend(cve_matches)

        # Check extracted results for CVE IDs
        for item in extracted:
            if isinstance(item, str):
                cve_matches = re.findall(r"CVE-\d{4}-\d{4,}", item)
                cves.extend(cve_matches)

        return list(set(cves))  # unique CVEs


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    from osintote.engine.stage import STAGE_REGISTRY

    if NucleiStage.NAME not in STAGE_REGISTRY:
        STAGE_REGISTRY[NucleiStage.NAME] = NucleiStage


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run nuclei scan from CLI."""
    import asyncio
    import sys
    import uuid

    if len(sys.argv) < 2:
        print("Usage: python -m osintote.workers.nuclei <target>")
        sys.exit(1)

    target = sys.argv[1]
    config = NucleiConfig(target=target)
    stage = NucleiStage(config)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=target)

    async def _run() -> None:
        result = await stage.execute(ctx, None)
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        if result.data:
            print(f"Records: {len(result.data)}")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
