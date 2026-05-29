# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""Relationships API — CRUD for target relationships (domain ↔ IP, etc).

Endpoints:
    GET    /api/relationships           — List all relationships
    POST   /api/relationships           — Create a relationship
    DELETE /api/relationships/{id}      — Delete a relationship
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from osintote.models.database import get_async_session
from osintote.models.orm import Relationship, RelationshipType, Target

router = APIRouter(prefix="/api/relationships", tags=["Relationships"])


class RelationshipCreateRequest(BaseModel):
    """Request body for creating a relationship."""

    source_id: str
    target_id: str
    type: str  # RelationshipType value


def _to_response(r: Relationship) -> dict[str, Any]:
    """Convert a Relationship ORM object to a dict."""
    return {
        "id": str(r.id),
        "source_id": str(r.source_id),
        "source_name": r.source.name if hasattr(r, "source") and r.source else None,
        "target_id": str(r.target_id),
        "target_name": r.target.name if hasattr(r, "target") and r.target else None,
        "type": r.type.value if hasattr(r.type, "value") else str(r.type),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("", response_model=list[dict])
async def list_relationships(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
    target_id: str | None = Query(None, description="Filter by target ID"),  # noqa: B008, RUF100
    rel_type: str | None = Query(None, description="Filter by type"),  # noqa: B008, RUF100
) -> list[dict]:
    """List all relationships with optional filters."""
    query = select(Relationship)

    if target_id:
        try:
            uid = UUID(target_id)
            query = query.where(
                (Relationship.source_id == uid) | (Relationship.target_id == uid)
            )
        except ValueError:
            pass

    if rel_type:
        with suppress(ValueError):
            query = query.where(Relationship.type == rel_type)

    relationships = db.exec(query).all()  # type: ignore[union-attr]
    return [_to_response(r) for r in relationships]


@router.post("", response_model=dict, status_code=201)
async def create_relationship(
    body: RelationshipCreateRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Create a relationship between two targets."""
    try:
        source_uid = UUID(body.source_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid source_id") from err

    try:
        target_uid = UUID(body.target_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid target_id") from err

    # Verify targets exist
    source = db.get(Target, source_uid)
    target = db.get(Target, target_uid)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source target {body.source_id} not found")
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target target {body.target_id} not found")

    # Create relationship
    relationship = Relationship(
        source_id=source_uid,
        target_id=target_uid,
        type=RelationshipType(body.type),
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)
    return _to_response(relationship)


@router.delete("/{rel_id}", response_model=dict)
async def delete_relationship(
    rel_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Delete a relationship."""
    try:
        uid = UUID(rel_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid relationship ID") from err

    rel = db.get(Relationship, uid)
    if rel is None:
        raise HTTPException(status_code=404, detail=f"Relationship {rel_id} not found")

    db.delete(rel)
    db.commit()
    return {"status": "deleted", "id": rel_id}
