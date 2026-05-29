# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""API key manager — CRUD operations for external service credentials.

Manages encrypted API key storage, primary/fallback key rotation,
and provides helper methods for looking up keys by source.

Usage::

    from sqlmodel import Session
    from osintote.api.manager import ApiKeyManager
    from osintote.models.orm import ApiKey

    with Session(engine) as session:
        manager = ApiKeyManager(session)
        key = manager.add(name="OpenAI Primary", source="openai", key="sk-...")
        keys = manager.list_by_source("openai")
        key = manager.rotate_primary("openai", "new-key")
        manager.delete(key)
"""

from __future__ import annotations

import logging
import uuid as uuid_module
from typing import Any

from sqlmodel import Session, select

from osintote.models.orm import ApiKey

logger = logging.getLogger(__name__)


class ApiKeyManager:
    """Manage API keys for external OSINT sources."""

    def __init__(self, session: Session) -> None:
        """Initialise with a database session.

        Parameters
        ----------
        session : Session
            The SQLModel session for database operations.
        """
        self.session = session

    def add(
        self,
        name: str,
        source: str,
        key: str,
        target_id: uuid_module.UUID | None = None,
        primary: bool = False,
        fallback: bool = False,
    ) -> ApiKey:
        """Add a new API key.

        Parameters
        ----------
        name : str
            Human-readable key name.
        source : str
            The OSINT source (e.g., "openai", "shodan", "virustotal").
        key : str
            The raw API key/credential.
        target_id : UUID | None
            Optional target association.
        primary : bool
            If True, mark as primary for this source.
        fallback : bool
            If True, mark as fallback key.

        Returns
        -------
        ApiKey
            The newly created API key record.
        """
        if primary:
            # Deactivate other primary keys for this source
            self._deactivate_primaries(source)

        api_key = ApiKey(
            name=name,
            source=source,
            key=key,
            target_id=target_id,
            primary=primary,
            fallback=fallback,
        )
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        logger.info("API key added: %s [%s]", name, source)
        return api_key

    def get(self, key_id: uuid_module.UUID) -> ApiKey | None:
        """Get an API key by ID.

        Parameters
        ----------
        key_id : UUID
            The API key UUID.

        Returns
        -------
        ApiKey | None
            The API key if found, None otherwise.
        """
        return self.session.get(ApiKey, key_id)

    def list_by_source(self, source: str) -> list[ApiKey]:
        """List all API keys for a given source.

        Parameters
        ----------
        source : str
            The OSINT source name.

        Returns
        -------
        list[ApiKey]
            All API keys for the source, ordered by creation date.
        """
        stmt = select(ApiKey).where(ApiKey.source == source).order_by(ApiKey.created_at)
        return list(self.session.execute(stmt).scalars().all())

    def list_all(self) -> list[ApiKey]:
        """List all API keys.

        Returns
        -------
        list[ApiKey]
            All API keys ordered by creation date.
        """
        stmt = select(ApiKey).order_by(ApiKey.created_at)
        return list(self.session.execute(stmt).scalars().all())

    def get_primary(self, source: str) -> ApiKey | None:
        """Get the primary API key for a source.

        Parameters
        ----------
        source : str
            The OSINT source name.

        Returns
        -------
        ApiKey | None
            The primary API key if one exists.
        """
        stmt = (
            select(ApiKey)
            .where(ApiKey.source == source, ApiKey.primary == True)  # noqa: E712
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def get_fallback(self, source: str) -> ApiKey | None:
        """Get the fallback API key for a source.

        Parameters
        ----------
        source : str
            The OSINT source name.

        Returns
        -------
        ApiKey | None
            The fallback API key if one exists.
        """
        stmt = (
            select(ApiKey)
            .where(ApiKey.source == source, ApiKey.fallback == True)  # noqa: E712
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def rotate_primary(
        self,
        source: str,
        new_key: str,
        new_name: str | None = None,
    ) -> ApiKey:
        """Rotate the primary API key for a source.

        Deactivates the current primary and sets up a new one.

        Parameters
        ----------
        source : str
            The OSINT source name.
        new_key : str
            The new API key value.
        new_name : str | None
            Optional new key name. Defaults to "{source} Primary".

        Returns
        -------
        ApiKey
            The newly rotated primary API key.
        """
        primary_name = new_name or f"{source} Primary"

        # Deactivate current primary
        self._deactivate_primaries(source)

        api_key = ApiKey(
            name=primary_name,
            source=source,
            key=new_key,
            primary=True,
        )
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        logger.info("Primary key rotated for %s: %s", source, api_key.name)
        return api_key

    def update(self, api_key: ApiKey, **kwargs: Any) -> ApiKey:
        """Update an existing API key.

        Parameters
        ----------
        api_key : ApiKey
            The API key to update.
        **kwargs
            Fields to update (name, key, primary, fallback).

        Returns
        -------
        ApiKey
            The updated API key.
        """
        for field, value in kwargs.items():
            if value is not None and hasattr(api_key, field):
                setattr(api_key, field, value)

        if kwargs.get("primary"):
            # Deactivate other primary keys for this source
            self._deactivate_primaries(api_key.source, exclude_id=api_key.id)

        self.session.commit()
        self.session.refresh(api_key)
        logger.info("API key updated: %s [%s]", api_key.name, api_key.source)
        return api_key

    def delete(self, api_key: ApiKey) -> None:
        """Delete an API key.

        Parameters
        ----------
        api_key : ApiKey
            The API key to delete.
        """
        logger.info("API key deleted: %s [%s]", api_key.name, api_key.source)
        self.session.delete(api_key)
        self.session.commit()

    def get_all_keys_for_source(self, source: str) -> dict[str, str | None]:
        """Get all keys for a source (primary + fallback).

        Returns a dict mapping "primary" and "fallback" to key values.

        Parameters
        ----------
        source : str
            The OSINT source name.

        Returns
        -------
        dict[str, str | None]
            Dict with "primary" and "fallback" key values.
        """
        keys: dict[str, str | None] = {"primary": None, "fallback": None}
        for key in self.list_by_source(source):
            if key.primary:
                keys["primary"] = key.key
            elif key.fallback:
                keys["fallback"] = key.key
        return keys

    def resolve_key(self, source: str) -> str | None:
        """Resolve an API key for a source using primary/fallback strategy.

        Returns the primary key if available, otherwise the fallback,
        otherwise None.

        Parameters
        ----------
        source : str
            The OSINT source name.

        Returns
        -------
        str | None
            The resolved API key value.
        """
        keys = self.get_all_keys_for_source(source)
        return keys.get("primary") or keys.get("fallback")

    def _deactivate_primaries(
        self,
        source: str,
        exclude_id: uuid_module.UUID | None = None,
    ) -> None:
        """Deactivate all primary keys for a source.

        Parameters
        ----------
        source : str
            The OSINT source name.
        exclude_id : UUID | None
            Optional ID to exclude from deactivation.
        """
        stmt = select(ApiKey).where(ApiKey.source == source, ApiKey.primary == True)  # noqa: E712
        if exclude_id:
            stmt = stmt.where(ApiKey.id != exclude_id)
        keys_to_update = list(self.session.execute(stmt).scalars().all())
        for k in keys_to_update:
            k.primary = False
            self.session.add(k)
