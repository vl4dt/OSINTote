# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
#
# SPDX-License-Identifier: MIT
"""Shared pytest fixtures for OSINTote tests."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine as sync_create_engine
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from osintote.api.app import app
from osintote.crypto import EncryptionManager, KeyStorage
from osintote.models.database import AsyncSessionLocal, engine as async_engine
from osintote.models.orm import (
    ApiKey,
    Error,
    Log,
    ModelBase,
    Record,
    Relationship,
    Setting,
    Target,
    Task,
    Webhook,
)


# ── Database fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def sqlite_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite database file with all tables."""
    db_file = tmp_path / "test.db"
    engine = sync_create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)
    return db_file


@pytest.fixture
def session(sqlite_db: Path) -> Session:
    """Create an in-memory SQLite session for ORM testing."""
    engine = sync_create_engine(f"sqlite:///{sqlite_db}")
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_target(session: Session) -> Target:
    """Create a sample target in the database."""
    target = Target(
        name="example.com",
        type="domain",
        raw="example.com",
        tags=["web", "production"],
        description="Test target",
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


@pytest.fixture
def sample_task(session: Session, sample_target: Target) -> Task:
    """Create a sample task linked to a target."""
    task = Task(
        name="Port scan",
        description="Scan ports on example.com",
        target_id=sample_target.id,
        status="running",
        engine="nmap",
        recipe="basic_scan",
        progress=50,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@pytest.fixture
def sample_record(session: Session, sample_target: Target) -> Record:
    """Create a sample record linked to a target."""
    record = Record(
        target_id=sample_target.id,
        type="dns",
        source="dns_enumeration",
        data={"nameserver": "ns1.example.com", "a_record": "93.184.216.34"},
        confidence=95,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@pytest.fixture
def sample_api_key(session: Session) -> ApiKey:
    """Create a sample API key."""
    api_key = ApiKey(
        name="Shodan Primary",
        source="shodan",
        key="test-api-key-12345",
        encrypted=False,
        primary=True,
        fallback=False,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return api_key


@pytest.fixture
def sample_setting(session: Session) -> Setting:
    """Create a sample setting."""
    setting = Setting(
        key="ai.default_provider",
        value={"provider": "openai", "model": "gpt-4"},
        description="Default AI provider",
    )
    session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


# ── API client fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def test_app():
    """Create the test application with lifespan disabled."""
    # Disable lifespan for tests (migrations would fail without DB)
    app.router.lifespan_on = False
    yield app
    app.router.lifespan_on = True


@pytest.fixture
async def async_client(test_app):
    """Create an async HTTP client for API testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_async_session():
    """Create a mock async session for dependency injection testing."""
    session = AsyncMock(spec=AsyncSessionLocal())
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# ── Crypto fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def encryption_manager(tmp_path: Path) -> EncryptionManager:
    """Create an EncryptionManager with a temporary key storage."""
    store = KeyStorage(tmp_path)
    return EncryptionManager(password="test-master-key", key_storage=store)


@pytest.fixture
def encrypted_blob(encryption_manager: EncryptionManager) -> Any:
    """Create an encrypted blob for testing."""
    return encryption_manager.encrypt(b"sensitive data")


# ── CLI fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def cli_test_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for CLI tests."""
    cli_dir = tmp_path / "cli_test_project"
    cli_dir.mkdir()
    return cli_dir


@pytest.fixture
def mock_console():
    """Mock the Rich console for CLI testing."""
    from unittest.mock import MagicMock

    console = MagicMock()
    console.print = MagicMock()
    console.input = MagicMock(return_value="n")
    return console


# ── Helper fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def tmp_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file."""
    f = tmp_path / "test.json"
    f.write_text("{}")
    return f


@pytest.fixture
def mock_asyncio_run(monkeypatch):
    """Patch asyncio.run to avoid event loop conflicts in tests."""
    original_run = asyncio.run

    def fake_run(coroutine, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coroutine)
        return original_run(coroutine, **kwargs)

    monkeypatch.setattr(asyncio, "run", fake_run)
    return fake_run
