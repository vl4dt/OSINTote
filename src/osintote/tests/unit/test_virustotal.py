# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for VirusTotal API source."""

from unittest.mock import AsyncMock, MagicMock, patch

from osintote.engine.stage import STAGE_REGISTRY, StageContext
from osintote.workers.virustotal import VirusTotalConfig, VirusTotalStage


class TestVirusTotalRegistration:
    """Test VirusTotal stage registration."""

    def test_virustotal_registered(self) -> None:
        """Test that VirusTotalStage is in STAGE_REGISTRY."""
        assert "virustotal" in STAGE_REGISTRY
        assert STAGE_REGISTRY["virustotal"] is VirusTotalStage

    def test_stage_properties(self) -> None:
        """Test stage default properties."""
        stage = VirusTotalStage()
        assert stage.name == "virustotal"
        assert stage.cost == "light"
        assert stage.max_results == 100
        assert stage.retry_delay == 0.25


class TestVirusTotalInit:
    """Test VirusTotal initialization."""

    def test_custom_api_key(self) -> None:
        """Test custom API key parameter."""
        stage = VirusTotalStage(api_key="test_key")
        assert stage.api_key == "test_key"

    def test_custom_domain(self) -> None:
        """Test custom domain parameter."""
        stage = VirusTotalStage(domain="example.com")
        assert stage.domain == "example.com"

    def test_custom_max_results(self) -> None:
        """Test custom max results."""
        stage = VirusTotalStage(max_results=50)
        assert stage.max_results == 50

    def test_custom_retry_delay(self) -> None:
        """Test custom retry delay."""
        stage = VirusTotalStage(retry_delay=0.5)
        assert stage.retry_delay == 0.5


def _make_vt_mocks(
    json_responses: list[dict],
    status_codes: list[int] | None = None,
):
    """Create mock httpx client and limiter for VirusTotal tests."""
    if status_codes is None:
        status_codes = [200] * len(json_responses)

    mocks = []
    for status, data in zip(status_codes, json_responses, strict=True):
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = data
        mocks.append(mock_resp)

    mock_limiter = AsyncMock()
    mock_limiter.__aenter__ = AsyncMock(return_value=mock_limiter)
    mock_limiter.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mocks)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    return mocks[0], mock_limiter, mock_client


class TestVirusTotalExecute:
    """Test VirusTotal execution."""

    def test_no_api_key(self) -> None:
        """Test failure when no API key is provided."""
        stage = VirusTotalStage()
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
        stage = VirusTotalStage(api_key="")
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
            patch("osintote.workers.virustotal.httpx.AsyncClient") as mock_client,
            patch("osintote.workers.virustotal.RateLimiterRegistry"),
        ):
            mock_client.side_effect = Exception("Network error")
            stage = VirusTotalStage(api_key="test_key", domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert not result.success
            assert "Network error" in result.error

    def test_domain_analysis_success(self) -> None:
        """Test successful domain analysis."""
        json_responses = [
            {"data": {"id": "example.com"}},
            {
                "data": {
                    "attributes": {
                        "last_analysis_results": {
                            "Avast": {"category": "malicious", "result": "Phishing"},
                            "Google": {"category": "clean", "result": "Clean"},
                        },
                        "last_analysis_stats": {
                            "malicious": 1,
                            "suspicious": 0,
                            "undetected": 5,
                            "harmless": 10,
                        },
                    },
                },
            },
            {"data": [{"id": "sub.example.com", "attributes": {"host_ip": "93.184.216.34"}}]},
            {"data": []},
        ]
        _mock_resp, mock_limiter, mock_client = _make_vt_mocks(json_responses)
        with (
            patch("osintote.workers.virustotal.httpx.AsyncClient", return_value=mock_client),
            patch("osintote.workers.virustotal.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = VirusTotalStage(
                api_key="test_key",
                domain="example.com",
                max_results=10,
            )
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.success
            assert result.records_count > 0

    def test_api_error_handling(self) -> None:
        """Test API error handling (401 unauthorized)."""
        json_responses = [{"data": {"id": "example.com"}}]
        _mock_resp, mock_limiter, mock_client = _make_vt_mocks(json_responses, [401])
        with (
            patch("osintote.workers.virustotal.httpx.AsyncClient", return_value=mock_client),
            patch("osintote.workers.virustotal.RateLimiterRegistry") as mock_reg,
        ):
            mock_reg.return_value.configure.return_value = mock_limiter
            stage = VirusTotalStage(api_key="invalid_key", domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)
            assert result.records_count == 0


class TestVirusTotalConfig:
    """Test VirusTotal configuration."""

    def test_default_values(self) -> None:
        """Test config default values."""
        config = VirusTotalConfig(api_key="test_key")
        assert config.api_key == "test_key"
        assert config.domain == ""
        assert config.max_results == 100
        assert config.retry_delay == 0.25

    def test_custom_values(self) -> None:
        """Test custom config values."""
        config = VirusTotalConfig(
            api_key="test_key",
            domain="example.com",
            max_results=50,
            retry_delay=0.5,
        )
        assert config.domain == "example.com"
        assert config.max_results == 50
        assert config.retry_delay == 0.5
