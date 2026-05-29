# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""API key routes — CRUD for external service credentials.

Endpoints:
    GET    /api/api-keys          — List all API keys
    GET    /api/api-keys/{id}     — Get API key details
    POST   /api/api-keys          — Create a new API key
    PUT    /api/api-keys/{id}     — Update an API key
    DELETE /api/api-keys/{id}     — Delete an API key
    PUT    /api/api-keys/{id}/rotate — Rotate primary key
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from osintote.api.manager import ApiKeyManager
from osintote.models.database import get_async_session

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


# ── Schemas ─────────────────────────────────────────────────────────────────


class ApiKeyCreate(BaseModel):
    """Request body for creating an API key."""

    name: str
    source: str
    key: str
    target_id: str | None = None
    primary: bool = False
    fallback: bool = False


class ApiKeyUpdate(BaseModel):
    """Request body for updating an API key."""

    name: str | None = None
    key: str | None = None
    primary: bool | None = None
    fallback: bool | None = None


class ApiKeyRotateRequest(BaseModel):
    """Request body for rotating an API key."""

    new_key: str
    new_name: str | None = None


# ── Routes ──────────────────────────────────────────────────────────────────


@router.get("", response_model=list[dict])
async def list_api_keys(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> list[dict]:
    """List all API keys."""
    manager = ApiKeyManager(db)
    keys = manager.list_all()

    return [
        {
            "id": str(k.id),
            "name": k.name,
            "source": k.source,
            "key": "****",
            "primary": k.primary,
            "fallback": k.fallback,
            "target_id": str(k.target_id) if k.target_id else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "updated_at": k.updated_at.isoformat() if k.updated_at else None,
        }
        for k in keys
    ]


@router.get("/{key_id}", response_model=dict)
async def get_api_key(
    key_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Get an API key by ID."""
    manager = ApiKeyManager(db)
    key = manager.get(uuid.UUID(key_id))

    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "id": str(key.id),
        "name": key.name,
        "source": key.source,
        "key": "****",
        "primary": key.primary,
        "fallback": key.fallback,
        "target_id": str(key.target_id) if key.target_id else None,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "updated_at": key.updated_at.isoformat() if key.updated_at else None,
    }


@router.post("", response_model=dict)
async def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Create a new API key."""
    manager = ApiKeyManager(db)

    target_id = None
    if body.target_id:
        target_id = uuid.UUID(body.target_id)

    key = manager.add(
        name=body.name,
        source=body.source,
        key=body.key,
        target_id=target_id,
        primary=body.primary,
        fallback=body.fallback,
    )

    return {
        "id": str(key.id),
        "name": key.name,
        "source": key.source,
        "key": "****",
        "primary": key.primary,
        "fallback": key.fallback,
        "target_id": str(key.target_id) if key.target_id else None,
    }


@router.put("/{key_id}", response_model=dict)
async def update_api_key(
    key_id: str,
    body: ApiKeyUpdate,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Update an API key."""
    manager = ApiKeyManager(db)
    key = manager.get(uuid.UUID(key_id))

    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    update_kwargs = {
        k: v for k, v in body.model_dump().items() if v is not None
    }

    key = manager.update(key, **update_kwargs)

    return {
        "id": str(key.id),
        "name": key.name,
        "source": key.source,
        "key": "****",
        "primary": key.primary,
        "fallback": key.fallback,
        "target_id": str(key.target_id) if key.target_id else None,
    }


@router.delete("/{key_id}", response_model=dict)
async def delete_api_key(
    key_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Delete an API key."""
    manager = ApiKeyManager(db)
    key = manager.get(uuid.UUID(key_id))

    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    manager.delete(key)
    return {"status": "deleted", "id": key_id}


@router.put("/{key_id}/rotate", response_model=dict)
async def rotate_api_key(
    key_id: str,
    body: ApiKeyRotateRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Rotate the primary API key for a source."""
    manager = ApiKeyManager(db)
    key = manager.get(uuid.UUID(key_id))

    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    rotated = manager.rotate_primary(
        source=key.source,
        new_key=body.new_key,
        new_name=body.new_name,
    )

    return {
        "id": str(rotated.id),
        "name": rotated.name,
        "source": rotated.source,
        "key": "****",
        "primary": rotated.primary,
        "fallback": rotated.fallback,
    }


@router.get("/resolve/{source}", response_model=dict)
async def resolve_api_key(
    source: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Resolve an API key for a source (primary + fallback).

    Returns which keys are available for the given source.
    """
    manager = ApiKeyManager(db)
    keys = manager.get_all_keys_for_source(source)
    resolved = manager.resolve_key(source)

    return {
        "source": source,
        "primary_available": keys["primary"] is not None,
        "fallback_available": keys["fallback"] is not None,
        "resolved": "****" if resolved else None,
    }
