# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the database module."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncSession

import osintote.models.database as db_module
from osintote.models.database import (
    AsyncSessionLocal,
    Base,
    engine,
    get_async_session,
    init_db,
)


class TestDatabaseSetup:
    """Tests for database configuration."""

    def test_database_url_set(self):
        """Test that DATABASE_URL is set."""
        assert hasattr(db_module, "DATABASE_URL")
        assert isinstance(db_module.DATABASE_URL, str)
        assert len(db_module.DATABASE_URL) > 0

    def test_engine_created(self):
        """Test that engine is created."""
        assert engine is not None

    def test_async_session_local_created(self):
        """Test that AsyncSessionLocal is created."""
        assert AsyncSessionLocal is not None


class TestBaseModel:
    """Tests for the Base class."""

    def test_base_is_declarative_base(self):
        """Test that Base is a SQLAlchemy DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)

    def test_base_metadata_exists(self):
        """Test that Base has a metadata attribute."""
        assert hasattr(Base, "metadata")


class TestInitDB:
    """Tests for init_db function."""

    def test_init_db_creates_tables(self, tmp_path: str):
        """Test that init_db creates all tables."""
        import os

        db_file = os.path.join(tmp_path, "init_test.db")
        db_url = f"sqlite+pysqlite:///{db_file}"
        # Monkeypatch DATABASE_URL
        original_url = db_module.DATABASE_URL
        try:
            db_module.DATABASE_URL = db_url
            init_db()
            assert os.path.exists(db_file)
        finally:
            db_module.DATABASE_URL = original_url

    def test_init_db_with_memory_db(self, tmp_path: str):
        """Test init_db with temporary database."""
        import os

        db_file = os.path.join(tmp_path, "test_init.db")
        db_url = f"sqlite+pysqlite:///{db_file}"
        original_url = db_module.DATABASE_URL
        try:
            db_module.DATABASE_URL = db_url
            init_db()
            # Verify tables were created
            sync_engine = create_engine(f"sqlite:///{db_file}")
            inspector = inspect(sync_engine)
            tables = inspector.get_table_names()
            assert "targets" in tables
        finally:
            db_module.DATABASE_URL = original_url

    def test_init_db_no_tables_before(self, tmp_path: str):
        """Test that init_db does not fail when no tables exist."""
        import os

        db_file = os.path.join(tmp_path, "test_no_tables.db")
        db_url = f"sqlite+pysqlite:///{db_file}"
        original_url = db_module.DATABASE_URL
        try:
            db_module.DATABASE_URL = db_url
            # Should not raise
            init_db()
            assert os.path.exists(db_file)
        finally:
            db_module.DATABASE_URL = original_url


class TestSessionDependency:
    """Tests for session dependency functions."""

    @pytest.mark.asyncio
    async def test_get_async_session_returns_async_gen(self):
        """Test that get_async_session returns an async generator."""
        import inspect

        result = get_async_session()
        assert inspect.isasyncgen(result)

    @pytest.mark.asyncio
    async def test_get_async_session_yields_session(self):
        """Test that get_async_session yields a session."""
        session_gen = get_async_session()
        session = await session_gen.__anext__()
        assert isinstance(session, AsyncSession)
        await session_gen.aclose()  # Proper cleanup

    @pytest.mark.asyncio
    async def test_session_close_works(self):
        """Test that session close() works without error."""
        session_gen = get_async_session()
        session = await session_gen.__anext__()
        await session.close()
        # If we got here without error, close() works

    @pytest.mark.asyncio
    async def test_session_has_engine(self):
        """Test that session has an engine."""
        session_gen = get_async_session()
        session = await session_gen.__anext__()
        assert session.get_bind() is not None
        await session.aclose()


class TestDatabaseURL:
    """Tests for database URL handling."""

    def test_default_url_is_sqlite(self):
        """Test that default URL uses SQLite."""
        assert "sqlite" in db_module.DATABASE_URL

    def test_url_can_be_changed(self):
        """Test that DATABASE_URL can be changed."""
        original = db_module.DATABASE_URL
        try:
            db_module.DATABASE_URL = "sqlite+aiosqlite:///./test.db"
            assert db_module.DATABASE_URL == "sqlite+aiosqlite:///./test.db"
        finally:
            db_module.DATABASE_URL = original
