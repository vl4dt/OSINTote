# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for Shodan API source."""

from unittest.mock import AsyncMock, MagicMock, patch

from osintote.engine.stage import STAGE_REGISTRY, StageContext
from osintote.workers.shodan import ShodanConfig, ShodanStage


class TestShodanRegistration:
    """Test Shodan stage registration."""

    def test_shodan_registered(self) -> None:
        """Test that ShodanStage is in STAGE_REGISTRY."""
        assert "shodan" in STAGE_REGISTRY
        assert STAGE_REGISTRY["shodan"] is ShodanStage

    def test_stage_properties(self) -> None:
        """Test stage default properties."""
        stage = ShodanStage()
        assert stage.name == "shodan"
        assert stage.cost == "medium"
        assert stage.max_results == 100
        assert stage.retry_delay == 1.0


class TestShodanInit:
    """Test Shodan initialization."""

    def test_custom_api_key(self) -> None:
        """Test custom API key parameter."""
        stage = ShodanStage(api_key="test_key")
        assert stage.api_key == "test_key"

    def test_custom_ip(self) -> None:
        """Test custom IP parameter."""
        stage = ShodanStage(ip="93.184.216.34")
        assert stage.ip == "93.184.216.34"

    def test_custom_domain(self) -> None:
        """Test custom domain parameter."""
        stage = ShodanStage(domain="example.com")
        assert stage.domain == "example.com"

    def test_custom_query(self) -> None:
        """Test custom query parameter."""
        stage = ShodanStage(query="port:443 country:US")
        assert stage.query == "port:443 country:US"

    def test_custom_max_results(self) -> None:
        """Test custom max results."""
        stage = ShodanStage(max_results=50)
        assert stage.max_results == 50

    def test_custom_retry_delay(self) -> None:
        """Test custom retry delay."""
        stage = ShodanStage(retry_delay=0.5)
        assert stage.retry_delay == 0.5


def _make_shodan_mocks(status_code: int = 200, json_data: dict | None = None):
    """Create mock httpx client and limiter for Shodan tests."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_data:
        mock_response.json.return_value = json_data
    else:
        mock_response.json.return_value = {}

    mock_limiter = AsyncMock()
    mock_limiter.__aenter__ = AsyncMock(return_value=mock_limiter)
    mock_limiter.__aexit__ = AsyncMock(return_value=False)

    async_cm = MagicMock()
    async_cm.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

    return mock_response, mock_limiter, async_cm


class TestShodanExecute:
    """Test Shodan execution."""

    def test_no_api_key(self) -> None:
        """Test failure when no API key is provided."""
        stage = ShodanStage()
        ctx = StageContext(
            task_id="test-task",
            target_id="test-target",
            target_name="example.com",
        )
        result = stage.execute(ctx)
        assert not result.success
        assert "api key" in result.error.lower()

    def test_missing_api_key(self) -> None:
        """Test failure when API key is empty."""
        stage = ShodanStage(api_key="")
        ctx = StageContext(
            task_id="test-task",
            target_id="test-target",
            target_name="example.com",
        )
        result = stage.execute(ctx)
        assert not result.success
        assert "api key" in result.error.lower()

    def test_api_call_failure(self) -> None:
        """Test handling of API call failures."""
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient") as mock_client,
            patch("osintote.workers.shodan.RateLimiterRegistry"),
        ):
            mock_client.side_effect = Exception("Network error")
            stage = ShodanStage(api_key="test_key", ip="93.184.216.34")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert not result.success
            assert "Network error" in result.error

    def test_host_lookup_success(self) -> None:
        """Test successful host lookup."""
        json_data = {
            "ip": "93.184.216.34",
            "hostname": "example.com",
            "org": "Example Corp",
            "country_name": "United States",
            "city": "New York",
            "os": "Ubuntu",
            "ports": [80, 443],
            "data": [
                {
                    "port": 80,
                    "product": "nginx",
                    "version": "1.18.0",
                    "data": "HTTP/1.1 200 OK",
                    "cpe": "cpe:/a:nginx:nginx:1.18.0",
                },
            ],
            "vulns": [],
        }
        _mock_resp, mock_limiter, async_cm = _make_shodan_mocks(200, json_data)
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient", return_value=async_cm),
            patch("osintote.workers.shodan.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = ShodanStage(api_key="test_key", ip="93.184.216.34")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            assert result.records_count > 0
            host_records = [r for r in result.data if r["type"] == "shodan-host"]
            assert len(host_records) > 0
            assert host_records[0]["data"]["ip"] == "93.184.216.34"
            assert host_records[0]["data"]["os"] == "Ubuntu"

    def test_service_records(self) -> None:
        """Test service record parsing."""
        json_data = {
            "ip": "93.184.216.34",
            "hostname": "example.com",
            "org": "Example Corp",
            "country_name": "US",
            "ports": [80],
            "data": [
                {
                    "port": 80,
                    "product": "nginx",
                    "version": "1.18.0",
                    "data": "HTTP/1.1 200 OK",
                },
            ],
            "vulns": [],
        }
        _mock_resp, mock_limiter, async_cm = _make_shodan_mocks(200, json_data)
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient", return_value=async_cm),
            patch("osintote.workers.shodan.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = ShodanStage(api_key="test_key", ip="93.184.216.34")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            service_records = [r for r in result.data if r["type"] == "shodan-service"]
            assert len(service_records) > 0
            assert service_records[0]["data"]["port"] == 80
            assert service_records[0]["data"]["product"] == "nginx"

    def test_vuln_records(self) -> None:
        """Test vulnerability record parsing."""
        json_data = {
            "ip": "93.184.216.34",
            "hostname": "example.com",
            "ports": [80],
            "data": [],
            "vulns": ["CVE-2021-44228"],
        }
        _mock_resp, mock_limiter, async_cm = _make_shodan_mocks(200, json_data)
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient", return_value=async_cm),
            patch("osintote.workers.shodan.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = ShodanStage(api_key="test_key", ip="93.184.216.34")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            vuln_records = [r for r in result.data if r["type"] == "shodan-vuln"]
            assert len(vuln_records) > 0
            assert vuln_records[0]["data"]["vulnerability"] == "CVE-2021-44228"

    def test_search_success(self) -> None:
        """Test search query execution."""
        json_data = {
            "total": 2,
            "matches": [
                {
                    "ip": "93.184.216.34",
                    "port": 80,
                    "org": "Example Corp",
                    "hostnames": ["example.com"],
                    "country_name": "United States",
                },
            ],
        }
        _mock_resp, mock_limiter, async_cm = _make_shodan_mocks(200, json_data)
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient", return_value=async_cm),
            patch("osintote.workers.shodan.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = ShodanStage(api_key="test_key", query="port:80", max_results=10)
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            search_records = [r for r in result.data if r["type"] == "shodan-search"]
            assert len(search_records) > 0
            assert search_records[0]["data"]["ip"] == "93.184.216.34"

    def test_404_response(self) -> None:
        """Test handling of 404 Not Found response."""
        _mock_resp, mock_limiter, async_cm = _make_shodan_mocks(404)
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient", return_value=async_cm),
            patch("osintote.workers.shodan.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = ShodanStage(api_key="test_key", ip="999.999.999.999")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            assert result.records_count == 0

    def test_401_unauthorized(self) -> None:
        """Test handling of 401 Unauthorized response."""
        _mock_resp, mock_limiter, async_cm = _make_shodan_mocks(401)
        with (
            patch("osintote.workers.shodan.httpx.AsyncClient", return_value=async_cm),
            patch("osintote.workers.shodan.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = ShodanStage(api_key="invalid_key", ip="93.184.216.34")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            assert result.records_count == 0


class TestShodanParseHost:
    """Test Shodan host data parsing."""

    def test_parse_host_data(self) -> None:
        """Test parsing Shodan host data."""
        host_data = {
            "ip": "93.184.216.34",
            "hostname": "example.com",
            "org": "Example Corp",
            "country_name": "United States",
            "city": "New York",
            "os": "Ubuntu",
            "ports": [80, 443],
            "data": [
                {
                    "port": 80,
                    "product": "nginx",
                    "version": "1.18.0",
                    "data": "HTTP/1.1 200 OK",
                },
            ],
            "vulns": [],
            "last_update": "2024-01-01T00:00:00",
        }
        records = ShodanStage._parse_host(host_data, "example.com")
        assert len(records) == 2
        assert records[0]["type"] == "shodan-host"
        assert records[0]["data"]["ip"] == "93.184.216.34"
        assert records[0]["data"]["os"] == "Ubuntu"
        assert records[0]["data"]["ports"] == [80, 443]
        assert records[1]["type"] == "shodan-service"
        assert records[1]["data"]["port"] == 80
        assert records[1]["data"]["product"] == "nginx"

    def test_parse_host_with_vulns(self) -> None:
        """Test parsing host data with vulnerabilities."""
        host_data = {
            "ip": "93.184.216.34",
            "hostname": "example.com",
            "ports": [],
            "data": [],
            "vulns": ["CVE-2021-44228", "CVE-2021-44229"],
        }
        records = ShodanStage._parse_host(host_data, "example.com")
        assert len(records) == 3
        vuln_records = [r for r in records if r["type"] == "shodan-vuln"]
        assert len(vuln_records) == 2
        assert vuln_records[0]["data"]["vulnerability"] == "CVE-2021-44228"


class TestShodanConfig:
    """Test Shodan configuration."""

    def test_default_values(self) -> None:
        """Test config default values."""
        config = ShodanConfig(api_key="test_key")
        assert config.api_key == "test_key"
        assert config.ip == ""
        assert config.max_results == 100
        assert config.retry_delay == 1.0

    def test_custom_values(self) -> None:
        """Test custom config values."""
        config = ShodanConfig(
            api_key="test_key",
            ip="93.184.216.34",
            max_results=50,
            retry_delay=0.5,
        )
        assert config.ip == "93.184.216.34"
        assert config.max_results == 50
        assert config.retry_delay == 0.5
