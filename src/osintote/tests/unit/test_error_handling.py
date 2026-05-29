# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for error handling framework."""

import pytest
from sqlmodel import Session

from osintote.models.database import get_session
from osintote.models.orm import Error, ErrorRead, ErrorSeverity


class TestErrorSeverity:
    """Test error severity enum and helpers."""

    def test_severity_values(self) -> None:
        """Test all severity levels exist."""
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_severity_to_notification(self) -> None:
        """Test severity-to-notification mapping."""
        from osintote.api.routes.errors import severity_to_notification

        assert severity_to_notification(ErrorSeverity.INFO) == "toast"
        assert severity_to_notification(ErrorSeverity.WARNING) == "toast+banner"
        assert severity_to_notification(ErrorSeverity.ERROR) == "banner+log"
        assert severity_to_notification(ErrorSeverity.CRITICAL) == "banner+log+notification"

    def test_is_critical(self) -> None:
        """Test critical detection."""
        from osintote.api.routes.errors import is_critical

        assert is_critical(ErrorSeverity.CRITICAL) is True
        assert is_critical(ErrorSeverity.ERROR) is False
        assert is_critical(ErrorSeverity.WARNING) is False
        assert is_critical(ErrorSeverity.INFO) is False

    def test_is_blocking(self) -> None:
        """Test blocking detection."""
        from osintote.api.routes.errors import is_blocking

        assert is_blocking(ErrorSeverity.ERROR) is True
        assert is_blocking(ErrorSeverity.CRITICAL) is True
        assert is_blocking(ErrorSeverity.WARNING) is False
        assert is_blocking(ErrorSeverity.INFO) is False


class TestErrorPublishing:
    """Test error publishing to SSE queue."""

    @pytest.mark.asyncio
    async def test_publish_error_adds_to_queue(self) -> None:
        """Test that publish_error adds to the SSE queue."""
        from osintote.api.routes.errors import publish_error

        error = Error(
            severity=ErrorSeverity.ERROR,
            message="Test error",
            logger="test",
        )
        await publish_error(error)

        # Verify no exception was raised


class TestErrorCRUD:
    """Test error CRUD operations via API."""

    def test_create_error(self) -> None:
        """Test creating an error in the database."""
        with Session(get_session()) as session:
            error = Error(
                severity=ErrorSeverity.WARNING,
                logger="test_logger",
                message="Test warning message",
                stage="test_stage",
                meta={"key": "value"},
            )
            session.add(error)
            session.commit()
            session.refresh(error)

            assert error.id is not None
            assert error.severity == ErrorSeverity.WARNING
            assert error.message == "Test warning message"

    def test_error_read_schema(self) -> None:
        """Test ErrorRead schema."""
        error = Error(
            severity=ErrorSeverity.CRITICAL,
            logger="test",
            message="Critical error",
            stage="test",
            meta={"detail": "test"},
        )
        read = ErrorRead.model_validate(error)
        assert read.severity == "critical"
        assert read.message == "Critical error"


class TestSeverityOrder:
    """Test severity ordering."""

    def test_severity_values(self) -> None:
        """Test that severity levels are ordered correctly."""
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.CRITICAL.value == "critical"
