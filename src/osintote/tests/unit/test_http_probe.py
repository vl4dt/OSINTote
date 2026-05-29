# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for HTTP probing stage."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from osintote.engine.stage import STAGE_REGISTRY, StageContext
from osintote.workers.http_probe import HttpProbeStage


class TestHttpProbeStageRegistration:
    """Test stage registration."""

    def test_http_probe_registered(self) -> None:
        """Test that HttpProbeStage is in STAGE_REGISTRY."""
        assert "http-probe" in STAGE_REGISTRY
        assert STAGE_REGISTRY["http-probe"] is HttpProbeStage

    def test_stage_properties(self) -> None:
        """Test stage default properties."""
        stage = HttpProbeStage()
        assert stage.name == "http-probe"
        assert stage.cost == "light"
        assert stage.timeout == 10.0
        assert stage.max_concurrent == 20
        assert stage.status_codes == [200, 301, 302]
        assert stage.paths == ["/"]
        assert stage.follow_redirects is True


class TestHttpProbeStageInit:
    """Test stage initialization with custom params."""

    def test_custom_timeout(self) -> None:
        """Test custom timeout parameter."""
        stage = HttpProbeStage(timeout=30.0)
        assert stage.timeout == 30.0

    def test_custom_status_codes(self) -> None:
        """Test custom status codes."""
        stage = HttpProbeStage(status_codes=[200, 404])
        assert stage.status_codes == [200, 404]

    def test_custom_paths(self) -> None:
        """Test custom probe paths."""
        stage = HttpProbeStage(paths=["/", "/api", "/admin"])
        assert stage.paths == ["/", "/api", "/admin"]

    def test_follow_redirects_false(self) -> None:
        """Test disabling redirect following."""
        stage = HttpProbeStage(follow_redirects=False)
        assert stage.follow_redirects is False


class TestHttpProbeStageExecute:
    """Test stage execution."""

    def test_execute_with_200_response(self) -> None:
        """Test successful HTTP probe with 200 response."""
        stage = HttpProbeStage(status_codes=[200])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-type": "text/html",
            "server": "nginx/1.19",
            "x-frame-options": "DENY",
        }
        mock_response.content = b"<html></html>"

        with patch("osintote.workers.http_probe.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            ctx = StageContext(
                target_name="example.com",
                target_id="00000000-0000-0000-0000-000000000001",
                task_id="00000000-0000-0000-0000-000000000002",
            )
            result = stage.execute(ctx)

            assert result.success is True
            assert result.records_count == 2
            assert len(result.data["alive_hosts"]) == 2
            assert len(ctx.records) == 2

    def test_execute_with_404_response(self) -> None:
        """Test HTTP probe with non-matching status code produces no records."""
        stage = HttpProbeStage(status_codes=[200])

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.content = b"Not Found"

        with patch("osintote.workers.http_probe.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            ctx = StageContext(
                target_name="example.com",
                target_id="00000000-0000-0000-0000-000000000001",
                task_id="00000000-0000-0000-0000-000000000002",
            )
            result = stage.execute(ctx)

            assert result.success is False
            assert result.records_count == 0
            assert len(ctx.records) == 0

    def test_execute_timeout(self) -> None:
        """Test HTTP probe with timeout error."""
        stage = HttpProbeStage()

        with patch("osintote.workers.http_probe.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("Timeout")
            )

            ctx = StageContext(
                target_name="example.com",
                target_id="00000000-0000-0000-0000-000000000001",
                task_id="00000000-0000-0000-0000-000000000002",
            )
            result = stage.execute(ctx)

            assert result.records_count == 2
            assert all(r.get("error") == "timeout" for r in ctx.records)

    def test_execute_request_error(self) -> None:
        """Test HTTP probe with connection error."""
        stage = HttpProbeStage()

        with patch("osintote.workers.http_probe.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            ctx = StageContext(
                target_name="example.com",
                target_id="00000000-0000-0000-0000-000000000001",
                task_id="00000000-0000-0000-0000-000000000002",
            )
            result = stage.execute(ctx)

            assert result.records_count == 2
            assert "error" in ctx.records[0]

    def test_build_urls_domain(self) -> None:
        """Test URL building for domain names."""
        stage = HttpProbeStage(paths=["/", "/api"])
        urls = stage._build_urls("example.com")
        assert "http://example.com/" in urls
        assert "https://example.com/" in urls
        assert "http://example.com/api" in urls
        assert "https://example.com/api" in urls

    def test_build_urls_ip(self) -> None:
        """Test URL building for IP addresses."""
        stage = HttpProbeStage(paths=["/", "/api"])
        urls = stage._build_urls("192.168.1.1")
        assert "http://192.168.1.1/" in urls
        assert "https://192.168.1.1/" in urls
        assert "http://192.168.1.1/api" in urls
        assert "https://192.168.1.1/api" in urls

    def test_capture_headers(self) -> None:
        """Test header capture."""
        stage = HttpProbeStage()

        mock_response = MagicMock()
        mock_response.headers = {
            "content-type": "text/html; charset=utf-8",
            "server": "nginx/1.19",
            "x-powered-by": "Express",
            "x-frame-options": "DENY",
            "content-security-policy": "default-src 'self'",
            "strict-transport-security": "max-age=31536000",
        }

        headers = stage._capture_headers(mock_response)
        assert headers["content-type"] == "text/html; charset=utf-8"
        assert headers["server"] == "nginx/1.19"
        assert headers["x-powered-by"] == "Express"
        assert headers["x-frame-options"] == "DENY"
        assert headers["content-security-policy"] == "default-src 'self'"
        assert headers["strict-transport-security"] == "max-age=31536000"


class TestHttpProbeStageIntegration:
    """Integration tests with real httpx (mocked)."""

    @pytest.mark.asyncio
    async def test_execute_with_mock_httpx(self) -> None:
        """Test stage with pytest-httpx mock transport."""
        stage = HttpProbeStage(status_codes=[200, 301, 302])

        ctx = StageContext(
            target_name="example.com",
            target_id="00000000-0000-0000-0000-000000000001",
            task_id="00000000-0000-0000-0000-000000000002",
        )

        with patch("osintote.workers.http_probe.httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.return_value = httpx.Response(200, json={"status": "ok"})
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            result = stage.execute(ctx)
            assert result.success is True
