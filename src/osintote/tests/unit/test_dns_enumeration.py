# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for DNS enumeration stage."""

from unittest.mock import MagicMock, patch

import dns.resolver
import pytest

from osintote.engine.stage import STAGE_REGISTRY, StageContext
from osintote.workers.dns_enumeration import DnsConfig, DnsEnumerationStage


class TestDnsEnumerationRegistration:
    """Test DNS enumeration stage registration."""

    def test_dns_enumeration_registered(self) -> None:
        """Test that DnsEnumerationStage is in STAGE_REGISTRY."""
        assert "dns-enumeration" in STAGE_REGISTRY
        assert STAGE_REGISTRY["dns-enumeration"] is DnsEnumerationStage

    def test_stage_properties(self) -> None:
        """Test stage default properties."""
        stage = DnsEnumerationStage(domain="example.com")
        assert stage.name == "dns-enumeration"
        assert stage.cost == "light"
        assert stage.timeout == 5.0
        assert stage.max_retries == 3
        assert stage.try_axfr is False
        assert stage.follow_cname is True
        assert "8.8.8.8" in stage.nameservers


class TestDnsEnumerationInit:
    """Test DNS enumeration initialization."""

    def test_custom_domain(self) -> None:
        """Test custom domain parameter."""
        stage = DnsEnumerationStage(domain="example.com")
        assert stage.domain == "example.com"

    def test_custom_timeout(self) -> None:
        """Test custom timeout."""
        stage = DnsEnumerationStage(timeout=30.0)
        assert stage.timeout == 30.0

    def test_axfr_enabled(self) -> None:
        """Test zone transfer flag."""
        stage = DnsEnumerationStage(try_axfr=True)
        assert stage.try_axfr is True

    def test_custom_nameservers(self) -> None:
        """Test custom nameservers."""
        ns = ["1.1.1.1", "1.0.0.1"]
        stage = DnsEnumerationStage(nameservers=ns)
        assert stage.nameservers == ns


class TestDnsEnumerationExecute:
    """Test DNS enumeration execution."""

    def test_dns_a_records(self) -> None:
        """Test A record discovery."""
        with patch("dns.resolver.Resolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver.resolve = MagicMock(return_value=[MagicMock(ttl=300)])
            mock_resolver_cls.return_value = mock_resolver

            stage = DnsEnumerationStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            assert result.records_count > 0
            a_records = [r for r in result.data if r["type"] == "dns-a"]
            assert len(a_records) > 0
            assert a_records[0]["data"]["record_type"] == "A"

    def test_dns_mx_records(self) -> None:
        """Test MX record discovery."""
        mx_mock = MagicMock()
        mx_mock.exchange = MagicMock()
        mx_mock.exchange.__str__ = MagicMock(return_value="mail.example.com.")
        mx_mock.preference = 10

        with patch("dns.resolver.Resolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver.resolve = MagicMock(return_value=[mx_mock])
            mock_resolver_cls.return_value = mock_resolver

            stage = DnsEnumerationStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            mx_records = [r for r in result.data if r["type"] == "dns-mx"]
            assert len(mx_records) > 0
            assert mx_records[0]["data"]["record_type"] == "MX"

    def test_dns_ns_records(self) -> None:
        """Test NS record discovery."""
        ns_mock = MagicMock()
        ns_mock.target = MagicMock()
        ns_mock.target.__str__ = MagicMock(return_value="ns1.example.com.")

        with patch("dns.resolver.Resolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver.resolve = MagicMock(return_value=[ns_mock])
            mock_resolver_cls.return_value = mock_resolver

            stage = DnsEnumerationStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            ns_records = [r for r in result.data if r["type"] == "dns-ns"]
            assert len(ns_records) > 0
            assert ns_records[0]["data"]["record_type"] == "NS"

    def test_dns_txt_records(self) -> None:
        """Test TXT record discovery."""
        txt_mock = MagicMock()
        txt_mock.strings = [b"v=spf1 include:_spf.example.com ~all"]

        with patch("dns.resolver.Resolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver.resolve = MagicMock(return_value=[txt_mock])
            mock_resolver_cls.return_value = mock_resolver

            stage = DnsEnumerationStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success
            txt_records = [r for r in result.data if r["type"] == "dns-txt"]
            assert len(txt_records) > 0
            assert "spf" in txt_records[0]["data"]["value"].lower()

    def test_dns_query_failure(self) -> None:
        """Test handling of DNS query failures."""
        def _resolve_side_effect(*args, **kwargs):
            if args[1] in ("A", "AAAA", "MX", "NS", "TXT"):
                raise Exception("NXDOMAIN")
            raise dns.resolver.NoAnswer  # SOA should fail gracefully

        with patch("dns.resolver.Resolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver.resolve = MagicMock(side_effect=_resolve_side_effect)
            mock_resolver_cls.return_value = mock_resolver

            stage = DnsEnumerationStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert result.success  # Stage succeeds even if some records fail
            assert result.metadata.get("errors") is not None

    def test_dns_enumeration_error(self) -> None:
        """Test complete failure of DNS enumeration."""
        import dns.resolver as real_resolver
        original_resolver = real_resolver.Resolver

        class BrokenResolver:
            def __init__(self, *args, **kwargs):
                pass
            def resolve(self, *args, **kwargs):
                raise Exception("DNS resolution failed")

        real_resolver.Resolver = BrokenResolver
        try:
            stage = DnsEnumerationStage(domain="example.com")
            ctx = StageContext(
                task_id="test-task",
                target_id="test-target",
                target_name="example.com",
            )
            result = stage.execute(ctx)

            assert not result.success
            assert "DNS resolution failed" in result.error
        finally:
            real_resolver.Resolver = original_resolver


class TestDnsConfig:
    """Test DNS configuration."""

    def test_default_nameservers(self) -> None:
        """Test default nameserver list."""
        config = DnsConfig(domain="example.com")
        assert config.nameservers == ["8.8.8.8", "8.8.4.4", "1.1.1.1"]

    def test_config_attributes(self) -> None:
        """Test config default values."""
        config = DnsConfig(domain="example.com", timeout=10.0, max_retries=5)
        assert config.domain == "example.com"
        assert config.timeout == 10.0
        assert config.max_retries == 5
        assert config.try_axfr is False
        assert config.follow_cname is True
