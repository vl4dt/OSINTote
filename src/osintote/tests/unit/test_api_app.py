# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the FastAPI application."""

from __future__ import annotations


class TestLifespan:
    """Tests for application lifespan."""

    def test_lifespan_manager_exists(self):
        """Test that lifespan manager exists."""
        from osintote.api.app import lifespan

        assert callable(lifespan)

    def test_lifespan_is_callable(self):
        """Test that lifespan is callable."""
        from osintote.api.app import lifespan

        result = lifespan(None)
        # lifespan returns a context manager
        assert result is not None


class TestFastAPISettings:
    """Tests for FastAPI application settings."""

    def test_app_is_fastapi_instance(self):
        """Test that app is a FastAPI instance."""
        from fastapi import FastAPI

        from osintote.api.app import app

        assert isinstance(app, FastAPI)

    def test_app_has_lifespan(self):
        """Test that app has lifespan configured."""
        from osintote.api.app import app

        assert app.router.lifespan_context is not None

    def test_app_has_middleware(self):
        """Test that app has middleware configured."""
        from osintote.api.app import app

        assert len(app.user_middleware) > 0

    def test_app_cors_configured(self):
        """Test that CORS middleware is configured."""
        from starlette.middleware.cors import CORSMiddleware

        from osintote.api.app import app

        # Check that CORSMiddleware is in the app's middleware stack
        has_cors = False
        for mw in app.user_middleware:
            if mw.cls == CORSMiddleware:
                has_cors = True
                break
        assert has_cors, "CORSMiddleware not configured"


class TestAPIEndpoints:
    """Tests for API endpoint registration."""

    def test_health_endpoint_registered(self):
        """Test that health endpoint is registered."""
        from osintote.api.app import app

        paths = [route.path for route in app.routes]
        assert "/api/health" in paths

    def test_health_endpoint_is_get(self):
        """Test that health endpoint uses GET method."""
        from osintote.api.app import app

        for route in app.routes:
            if route.path == "/api/health":
                assert "GET" in route.methods


class TestAppConfig:
    """Tests for app configuration."""

    def test_app_has_docs(self):
        """Test that API docs endpoint exists."""
        from osintote.api.app import app

        paths = [route.path for route in app.routes]
        assert "/api/docs" in paths or "/docs" in paths

    def test_app_has_openapi_json(self):
        """Test that OpenAPI JSON endpoint exists."""
        from osintote.api.app import app

        paths = [route.path for route in app.routes]
        assert "/api/openapi.json" in paths or "/openapi.json" in paths

    def test_app_has_title(self):
        """Test that app has a title."""
        from fastapi import FastAPI

        from osintote.api.app import app

        assert isinstance(app, FastAPI)
        assert app.title == "OSINTote"
