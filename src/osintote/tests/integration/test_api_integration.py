# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Integration tests for the FastAPI application."""

from __future__ import annotations


class TestAPIStructure:
    """Integration tests that test the full stack."""

    def test_app_routes_exist(self):
        """Test that API routes are registered."""
        from osintote.api.app import app

        paths = [route.path for route in app.routes]
        assert "/api/health" in paths
        assert "/api/docs" in paths or "/docs" in paths
        assert "/api/openapi.json" in paths or "/openapi.json" in paths

    def test_openapi_schema_exists(self):
        """Test that OpenAPI schema is generated."""
        from osintote.api.app import app

        schema = app.openapi()
        assert "info" in schema
        assert "paths" in schema
        assert schema["info"]["title"] == "OSINTote"

    def test_health_endpoint_in_schema(self):
        """Test that health endpoint is in OpenAPI schema."""
        from osintote.api.app import app

        schema = app.openapi()
        paths = schema.get("paths", {})
        # Find health endpoint path (could be /api/health or similar)
        health_paths = [p for p in paths if "health" in p]
        assert len(health_paths) > 0

    def test_app_has_info(self):
        """Test that OpenAPI has info section."""
        from osintote.api.app import app

        schema = app.openapi()
        assert "info" in schema
        assert schema["info"]["title"] == "OSINTote"
