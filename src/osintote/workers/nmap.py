# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""nmap wrapper — port scanning stage.

Uses the CLI wrapper framework to execute ``nmap`` safely with
``asyncio.create_subprocess_exec``.  Parses XML output (``-oX``)
and normalises results to :class:`osintote.models.orm.Record` dicts.

Example::

    stage = NmapStage(host="192.168.1.1", ports="22,80,443")
    records = await stage.execute(ctx, executor)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

from osintote.cli.wrapper import SubprocessRunner
from osintote.engine.stage import StageContext, StageResult

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class NmapConfig:
    """Configuration for an nmap scan."""

    host: str
    ports: str = "22,80,443,8080"
    timing: str = "T3"
    scan_type: str = "-Pn -sV"
    output_format: str = "-oX -"
    timeout: float = 120.0
    extra_args: list[str] = field(default_factory=list)

    @property
    def full_args(self) -> list[str]:
        """All nmap CLI arguments."""
        args = ["nmap", self.host]
        args.extend(self.scan_type.split())
        args.extend(["-p", self.ports])
        args.extend(["-T", self.timing])
        args.extend(["-oX", "-"])  # XML to stdout
        args.extend(self.extra_args)
        return args


# ── Stage ───────────────────────────────────────────────────────────────────


class NmapStage:
    """nmap port-scanning stage.

    Executes ``nmap`` via :class:`osintote.cli.wrapper.SubprocessRunner`,
    parses the XML output, and produces :class:`StageResult` records.
    """

    NAME = "nmap"

    def __init__(self, config: NmapConfig) -> None:
        self.config = config
        self.runner = SubprocessRunner()

    async def execute(
        self, ctx: StageContext, executor: Any
    ) -> StageResult:
        """Run nmap and return normalised records."""
        try:
            result = await self.runner.run_safe(
                *self.config.full_args,
                timeout=self.config.timeout,
            )

            if not result.success:
                return StageResult.failure(
                    error=result.stderr.strip(),
                    message=result.stderr.strip(),
                )

            records = self._parse_xml(result.stdout)

            return StageResult.success_result(
                data=records,
                records_count=len(records),
                message=f"Scanned {len(records)} ports",
            )

        except Exception as exc:
            return StageResult.failure(
                error=str(exc),
                message=str(exc),
            )

    @staticmethod
    def _parse_xml(xml_text: str) -> list[dict[str, Any]]:
        """Parse nmap XML output into record dicts."""
        records: list[dict[str, Any]] = []
        try:
            root = etree.fromstring(xml_text.encode() if isinstance(xml_text, str) else xml_text)
        except Exception:
            return records

        hosts = root.xpath("//host")
        for host in hosts:
            addr_elem = host.find("address")
            if addr_elem is None:
                continue
            addr = addr_elem.get("addr", "")
            host_state = host.find("status")
            if host_state is None:
                continue
            host_status = host_state.get("state", "down")

            if host_status == "up":
                ports_elem = host.find("ports")
                if ports_elem is not None:
                    for port in ports_elem.findall("port"):
                        proto = port.get("protocol", "tcp")
                        port_num = int(port.get("portid", 0))
                        state_elem = port.find("state")
                        port_state = (
                            state_elem.get("state", "closed")
                            if state_elem is not None
                            else "closed"
                        )
                        service = port.find("service")
                        service_name = service.get("name", "") if service is not None else ""
                        service_version = service.get("version", "") if service is not None else ""

                        record = {
                            "id": str(__import__("uuid", fromlist=["uuid4"]).uuid4()),
                            "type": "port",
                            "target": addr,
                            "data": {
                                "port": port_num,
                                "protocol": proto,
                                "state": port_state,
                                "service": service_name,
                                "version": service_version,
                            },
                        }
                        records.append(record)

        return records


# ── Registry ────────────────────────────────────────────────────────────────


def __register__() -> None:  # noqa: N807
    """Register this stage with the STAGE_REGISTRY."""
    from osintote.engine.stage import STAGE_REGISTRY

    if NmapStage.NAME not in STAGE_REGISTRY:
        STAGE_REGISTRY[NmapStage.NAME] = NmapStage


# ── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run nmap scan from CLI."""
    import asyncio
    import sys
    import uuid

    if len(sys.argv) < 3:
        print("Usage: python -m osintote.workers.nmap <host> <ports>")
        sys.exit(1)

    host = sys.argv[1]
    ports = sys.argv[2]
    config = NmapConfig(host=host, ports=ports)
    stage = NmapStage(config)
    task_id = uuid.uuid4()
    target_id = uuid.uuid4()
    ctx = StageContext(task_id=task_id, target_id=target_id, target_name=host)

    async def _run() -> None:
        result = await stage.execute(ctx, None)
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        if result.data:
            print(f"Records: {len(result.data)}")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
