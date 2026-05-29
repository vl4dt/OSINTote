# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the worker stages (nmap, subfinder, nuclei)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from osintote.workers.nmap import NmapConfig, NmapStage
from osintote.workers.nuclei import NucleiConfig, NucleiStage
from osintote.workers.subfinder import SubfinderConfig, SubfinderStage

# ── Nmap tests ──────────────────────────────────────────────────────────────


class TestNmapConfig:
    """Tests for NmapConfig."""

    def test_full_args(self) -> None:
        """Full args should include nmap, host, scan options."""
        config = NmapConfig(host="192.168.1.1", ports="22,80", timing="T4")
        args = config.full_args
        assert args[0] == "nmap"
        assert "192.168.1.1" in args
        assert "-p" in args
        assert "22,80" in args
        assert "-oX" in args


class TestNmapStage:
    """Tests for NmapStage."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Successful nmap scan should return completed result."""
        config = NmapConfig(host="192.168.1.1", ports="22")
        stage = NmapStage(config)

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = '<nmaprun><host><address addr="192.168.1.1"/><status state="up"/><ports><port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port></ports></host></nmaprun>'  # noqa: E501
        mock_result.stderr = ""

        stage.runner = MagicMock()
        stage.runner.run_safe = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        result = await stage.execute(ctx, None)

        assert result.success is True
        assert result.records_count == 1

    @pytest.mark.asyncio
    async def test_execute_failure(self) -> None:
        """Failed nmap scan should return failed result."""
        config = NmapConfig(host="192.168.1.1", ports="22")
        stage = NmapStage(config)

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stdout = ""
        mock_result.stderr = "nmap: command not found"

        stage.runner = MagicMock()
        stage.runner.run_safe = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        result = await stage.execute(ctx, None)

        assert result.success is False


class TestNmapXMLParsing:
    """Tests for nmap XML parsing."""

    def test_parse_xml_single_port(self) -> None:
        """Parse XML with single port."""
        xml = '<nmaprun><host><address addr="192.168.1.1"/><status state="up"/><ports><port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port></ports></host></nmaprun>'  # noqa: E501
        records = NmapStage._parse_xml(xml)
        assert len(records) == 1
        assert records[0]["type"] == "port"
        assert records[0]["data"]["port"] == 22
        assert records[0]["data"]["state"] == "open"
        assert records[0]["data"]["service"] == "ssh"

    def test_parse_xml_multiple_ports(self) -> None:
        """Parse XML with multiple ports."""
        xml = '<nmaprun><host><address addr="192.168.1.1"/><status state="up"/><ports><port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port><port protocol="tcp" portid="80"><state state="open"/><service name="http"/></port></ports></host></nmaprun>'  # noqa: E501
        records = NmapStage._parse_xml(xml)
        assert len(records) == 2
        assert records[0]["data"]["port"] == 22
        assert records[1]["data"]["port"] == 80

    def test_parse_xml_closed_port(self) -> None:
        """Parse XML with closed port."""
        xml = '<nmaprun><host><address addr="192.168.1.1"/><status state="up"/><ports><port protocol="tcp" portid="443"><state state="closed"/></port></ports></host></nmaprun>'  # noqa: E501
        records = NmapStage._parse_xml(xml)
        assert len(records) == 1
        assert records[0]["data"]["state"] == "closed"

    def test_parse_xml_down_host(self) -> None:
        """Parse XML with down host should return empty."""
        xml = '<nmaprun><host><status state="down"/></host></nmaprun>'
        records = NmapStage._parse_xml(xml)
        assert len(records) == 0

    def test_parse_xml_invalid(self) -> None:
        """Invalid XML should return empty."""
        records = NmapStage._parse_xml("invalid xml")
        assert len(records) == 0


# ── Subfinder tests ─────────────────────────────────────────────────────────


class TestSubfinderConfig:
    """Tests for SubfinderConfig."""

    def test_full_args(self) -> None:
        """Full args should include subfinder, -d, domain."""
        config = SubfinderConfig(domain="example.com")
        args = config.full_args
        assert args[0] == "subfinder"
        assert "-d" in args
        assert "example.com" in args


class TestSubfinderStage:
    """Tests for SubfinderStage."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Successful subfinder run should return completed result."""
        config = SubfinderConfig(domain="example.com")
        stage = SubfinderStage(config)

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = "www.example.com\napi.example.com\ntest.example.com\n"
        mock_result.stderr = ""

        stage.runner = MagicMock()
        stage.runner.run_safe = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        result = await stage.execute(ctx, None)

        assert result.success is True
        assert result.records_count == 3

    @pytest.mark.asyncio
    async def test_execute_failure(self) -> None:
        """Failed subfinder run should return failed result."""
        config = SubfinderConfig(domain="example.com")
        stage = SubfinderStage(config)

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stdout = ""
        mock_result.stderr = "subfinder not found"

        stage.runner = MagicMock()
        stage.runner.run_safe = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        result = await stage.execute(ctx, None)

        assert result.success is False


class TestSubfinderOutputParsing:
    """Tests for subfinder output parsing."""

    def test_parse_output(self) -> None:
        """Parse subfinder stdout for subdomains."""
        output = "www.example.com\napi.example.com\n\n  test.example.com  \n"
        result = SubfinderStage._parse_output(output)
        assert "www.example.com" in result
        assert "api.example.com" in result
        assert "test.example.com" in result
        assert "" not in result

    def test_dedup(self) -> None:
        """Deduplicate subdomains preserving order."""
        subdomains = ["www.example.com", "WWW.EXAMPLE.COM", "api.example.com"]
        result = SubfinderStage._dedup(subdomains)
        assert result == ["www.example.com", "api.example.com"]


# ── Nuclei tests ────────────────────────────────────────────────────────────


class TestNucleiConfig:
    """Tests for NucleiConfig."""

    def test_full_args(self) -> None:
        """Full args should include nuclei, -u, -json."""
        config = NucleiConfig(target="https://example.com")
        args = config.full_args
        assert args[0] == "nuclei"
        assert "-u" in args
        assert "https://example.com" in args
        assert "-json" in args

    def test_severity_filter(self) -> None:
        """Severity filter should be passed to CLI."""
        config = NucleiConfig(target="https://example.com", severity=["high", "critical"])
        args = config.full_args
        assert "-severity" in args
        assert "high,critical" in args


class TestNucleiStage:
    """Tests for NucleiStage."""

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Successful nuclei scan should return completed result."""
        config = NucleiConfig(target="https://example.com")
        stage = NucleiStage(config)

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.stdout = json.dumps({
            "templateID": "CVE-2021-44228",
            "info": {"name": "Log4j RCE", "severity": "critical"},
            "host": "https://example.com",
        }) + "\n"
        mock_result.stderr = ""

        stage.runner = MagicMock()
        stage.runner.run_safe = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        result = await stage.execute(ctx, None)

        assert result.success is True
        assert result.records_count == 1
        assert result.data[0]["type"] == "vulnerability"

    @pytest.mark.asyncio
    async def test_execute_failure(self) -> None:
        """Failed nuclei scan should return failed result."""
        config = NucleiConfig(target="https://example.com")
        stage = NucleiStage(config)

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.stdout = ""
        mock_result.stderr = "nuclei not found"

        stage.runner = MagicMock()
        stage.runner.run_safe = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        result = await stage.execute(ctx, None)

        assert result.success is False


class TestNucleiJSONLParsing:
    """Tests for nuclei JSONL parsing."""

    def test_parse_jsonl_single_finding(self) -> None:
        """Parse single JSONL line."""
        jsonl = json.dumps({
            "templateID": "CVE-2021-44228",
            "info": {"name": "Log4j RCE", "severity": "critical"},
            "host": "https://example.com",
        }) + "\n"
        findings = NucleiStage._parse_jsonl(jsonl)
        assert len(findings) == 1
        assert findings[0]["templateID"] == "CVE-2021-44228"

    def test_parse_jsonl_multiple_findings(self) -> None:
        """Parse multiple JSONL lines."""
        jsonl = json.dumps({"templateID": "CVE-2021-44228", "info": {"severity": "critical"}}) + "\n"
        jsonl += json.dumps({"templateID": "CVE-2021-33333", "info": {"severity": "high"}}) + "\n"
        findings = NucleiStage._parse_jsonl(jsonl)
        assert len(findings) == 2

    def test_parse_jsonl_blank_lines(self) -> None:
        """Blank lines should be skipped."""
        jsonl = json.dumps({"templateID": "test"}) + "\n\n\n"
        findings = NucleiStage._parse_jsonl(jsonl)
        assert len(findings) == 1

    def test_extract_cves(self) -> None:
        """Extract CVE IDs from a finding."""
        finding = {
            "metadata": {"cve_id": "CVE-2021-44228"},
            "extracted-results": ["Affected: CVE-2021-33333"],
        }
        cves = NucleiStage.extract_cves(finding)
        assert "CVE-2021-44228" in cves
        assert "CVE-2021-33333" in cves
