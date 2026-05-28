"""Database connection and session management.

Provides async and sync engines, a session factory, and an auto-migrate
hook that runs Alembic upgrades at startup.

Usage::

    from osintote.models.database import AsyncSessionLocal, get_async_session, Base

    # In an async FastAPI app:
    app = FastAPI()

    @app.on_event(\"startup\")
    async def startup():
        await Base.metadata.create_all(engine)

    @app.get(\"/items\")
    async def read_items(session: AsyncSession = Depends(get_async_session)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlmodel import SQLModel

# ── engine setup ─────────────────────────────────────────────────────

# Use sqlite+aiosqlite for async support; replace with postgresql+asyncpg
# in production.
DATABASE_URL: str = "sqlite+aiosqlite:///./osintote.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={
        "check_same_thread": False,  # SQLite-specific; irrelevant for aiosqlite
    },
)

# Thread-safe async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── base class ───────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """Base class for all ORM models (SQLAlchemy 2.0 style)."""

    pass


# ── session dependency ───────────────────────────────────────────────


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database sessions.

    Yields a session and ensures it is closed after the request.
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


# ── auto-migrate helper ──────────────────────────────────────────────


async def auto_migrate() -> None:
    """Run Alembic 'upgrade head' to apply any pending migrations.

    Call this at application startup so the database schema is always
    up-to-date without manual ``alembic upgrade head``.
    """
    import asyncio

    from alembic.config import Config
    from alembic.command import upgrade as alembic_upgrade

    alembic_cfg = Config("alembic.ini")
    await asyncio.to_thread(alembic_upgrade, alembic_cfg, "head")


def init_db() -> None:
    """Create all tables if they do not exist (development convenience).

    In production, prefer auto_migrate() which runs Alembic migrations.
    This function is provided as a quick way to bootstrap the database
    for local development without running migrations.
    """
    import asyncio

    # Use sync engine for table creation (simpler for SQLite)
    from sqlalchemy import create_engine as sync_create_engine

    sync_url = DATABASE_URL.replace("aiosqlite", "pysqlite")
    sync_engine = sync_create_engine(sync_url)
    SQLModel.metadata.create_all(sync_engine)
