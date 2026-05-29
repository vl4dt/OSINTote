# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for WHOIS stage."""

from unittest.mock import MagicMock, patch

import pytest

from osintote.engine.stage import STAGE_REGISTRY, StageContext
from osintote.workers.whois import WhoisConfig, WhoisStage


class TestWhoisRegistration:
    """Test WHOIS stage registration."""

    def test_whois_registered(self) -> None:
        """Test that WhoisStage is in STAGE_REGISTRY."""
        assert "whois" in STAGE_REGISTRY
        assert STAGE_REGISTRY["whois"] is WhoisStage

    def test_stage_properties(self) -> None:
        """Test stage default properties."""
        stage = WhoisStage()
        assert stage.name == "whois"
        assert stage.cost == "light"
        assert stage.timeout == 10.0
        assert stage.max_retries == 3


class TestWhoisInit:
    """Test WHOIS initialization."""

    def test_custom_domain(self) -> None:
        """Test custom domain parameter."""
        stage = WhoisStage(domain="example.com")
        assert stage.domain == "example.com"

    def test_custom_timeout(self) -> None:
        """Test custom timeout."""
        stage = WhoisStage(timeout=30.0)
        assert stage.timeout == 30.0

    def test_custom_retries(self) -> None:
        """Test custom retry count."""
        stage = WhoisStage(max_retries=5)
        assert stage.max_retries == 5


class TestWhoisExecute:
    """Test WHOIS execution."""

    def test_whois_success(self) -> None:
        """Test successful WHOIS lookup."""
        whois_mock = MagicMock()
        whois_mock.domain_name = "EXAMPLE.COM"
        whois_mock.registrar = "Example Registrar Inc."
        whois_mock.creation_date = MagicMock()
        whois_mock.creation_date.isoformat = MagicMock(return_value="2020-01-01T00:00:00")
        whois_mock.expiration_date = MagicMock()
        whois_mock.expiration_date.isoformat = MagicMock(return_value="2025-01-01T00:00:00")
        whois_mock.name_servers = ["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"]
        whois_mock.status = ["clientTransferProhibited"]
        whois_mock.updated_date = MagicMock()
        whois_mock.updated_date.isoformat = MagicMock(return_value="2023-01-01T00:00:00")

        with patch("whois.whois", return_value=whois_mock):
            stage = WhoisStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            assert result.records_count == 1
            assert result.data["data"]["domain"] == "EXAMPLE.COM"
            assert result.data["data"]["registrar"] == "Example Registrar Inc."

    def test_whois_with_target_name(self) -> None:
        """Test WHOIS using context target name."""
        whois_mock = MagicMock()
        whois_mock.domain_name = "EXAMPLE.COM"
        whois_mock.registrar = "Registrar"
        whois_mock.creation_date = MagicMock()
        whois_mock.creation_date.isoformat = MagicMock(return_value="2020-01-01T00:00:00")
        whois_mock.expiration_date = MagicMock()
        whois_mock.expiration_date.isoformat = MagicMock(return_value="2025-01-01T00:00:00")
        whois_mock.name_servers = []
        whois_mock.status = []
        whois_mock.updated_date = MagicMock()
        whois_mock.updated_date.isoformat = MagicMock(return_value="2023-01-01T00:00:00")

        with patch("whois.whois", return_value=whois_mock):
            stage = WhoisStage()
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            assert result.data["target"] == "example.com"

    def test_whois_lookup_failure(self) -> None:
        """Test WHOIS lookup failure."""
        with patch("whois.whois", side_effect=Exception("WHOIS query timeout")):
            stage = WhoisStage(domain="example.com", max_retries=1)
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert not result.success
            assert "WHOIS query timeout" in result.error

    def test_whois_retry_on_failure(self) -> None:
        """Test WHOIS retry logic on failure."""
        call_count = 0

        def _fail_then_succeed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            whois_mock = MagicMock()
            whois_mock.domain_name = "EXAMPLE.COM"
            whois_mock.registrar = "Registrar"
            whois_mock.creation_date = MagicMock()
            whois_mock.creation_date.isoformat = MagicMock(return_value="2020-01-01T00:00:00")
            whois_mock.expiration_date = MagicMock()
            whois_mock.expiration_date.isoformat = MagicMock(return_value="2025-01-01T00:00:00")
            whois_mock.name_servers = []
            whois_mock.status = []
            whois_mock.updated_date = MagicMock()
            whois_mock.updated_date.isoformat = MagicMock(return_value="2023-01-01T00:00:00")
            return whois_mock

        with patch("whois.whois", side_effect=_fail_then_succeed):
            stage = WhoisStage(domain="example.com", max_retries=3)
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            assert call_count == 3


class TestWhoisParse:
    """Test WHOIS data parsing."""

    def test_parse_whois_data(self) -> None:
        """Test parsing WHOIS data into structured record."""
        whois_mock = MagicMock()
        whois_mock.domain_name = "EXAMPLE.COM"
        whois_mock.registrar = "Example Registrar Inc."
        whois_mock.creation_date = MagicMock()
        whois_mock.creation_date.isoformat = MagicMock(return_value="2020-01-01T00:00:00")
        whois_mock.expiration_date = MagicMock()
        whois_mock.expiration_date.isoformat = MagicMock(return_value="2025-01-01T00:00:00")
        whois_mock.name_servers = ["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"]
        whois_mock.status = ["clientTransferProhibited"]
        whois_mock.updated_date = MagicMock()
        whois_mock.updated_date.isoformat = MagicMock(return_value="2023-01-01T00:00:00")

        record = WhoisStage._parse_whois(whois_mock, "example.com")

        assert record["type"] == "whois"
        assert record["target"] == "example.com"
        assert record["data"]["domain"] == "EXAMPLE.COM"
        assert record["data"]["registrar"] == "Example Registrar Inc."
        assert record["data"]["name_servers"] == ["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"]
        assert record["data"]["status"] == ["clientTransferProhibited"]

    def test_parse_whois_minimal_data(self) -> None:
        """Test parsing minimal WHOIS data."""
        whois_mock = MagicMock()
        whois_mock.domain_name = "EXAMPLE.COM"
        for attr in ["registrar", "creation_date", "expiration_date",
                      "name_servers", "status", "updated_date"]:
            setattr(whois_mock, attr, None)

        record = WhoisStage._parse_whois(whois_mock, "example.com")

        assert record["data"]["domain"] == "EXAMPLE.COM"
        assert "registrar" not in record["data"]
        assert record["data"]["name_servers"] == []


class TestWhoisConfig:
    """Test WHOIS configuration."""

    def test_default_values(self) -> None:
        """Test config default values."""
        config = WhoisConfig(domain="example.com")
        assert config.domain == "example.com"
        assert config.timeout == 10.0
        assert config.max_retries == 3

    def test_custom_values(self) -> None:
        """Test custom config values."""
        config = WhoisConfig(domain="example.com", timeout=30.0, max_retries=5)
        assert config.domain == "example.com"
        assert config.timeout == 30.0
        assert config.max_retries == 5
