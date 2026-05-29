# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""Target CRUD API — create, list, update, delete targets.

Endpoints:
    GET    /api/targets             — List all targets
    GET    /api/targets/{id}        — Get target details
    POST   /api/targets             — Create a new target
    PUT    /api/targets/{id}        — Update a target
    DELETE /api/targets/{id}        — Delete a target
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from osintote.models.database import get_async_session
from osintote.models.orm import Target

router = APIRouter(prefix="/api/targets", tags=["Targets"])


class TargetCreateRequest(BaseModel):
    """Request body for creating a target."""

    name: str
    type: str
    raw: str | None = None
    tags: list[str] = []
    description: str | None = None


class TargetUpdateRequest(BaseModel):
    """Request body for updating a target."""

    name: str | None = None
    type: str | None = None
    raw: str | None = None
    tags: list[str] | None = None
    description: str | None = None


class TargetResponse(BaseModel):
    """Target API response."""

    id: str
    name: str
    type: str
    raw: str | None = None
    tags: list[str] = []
    description: str | None = None
    record_count: int = 0
    task_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


def _to_response(t: Target) -> dict[str, Any]:
    """Convert a Target ORM object to a dict."""
    return {
        "id": str(t.id),
        "name": t.name,
        "type": t.type,
        "raw": t.raw,
        "tags": t.tags or [],
        "description": t.description,
        "record_count": len(t.records) if hasattr(t, "records") and t.records else 0,
        "task_count": len(t.tasks) if hasattr(t, "tasks") and t.tasks else 0,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("", response_model=list[dict])
async def list_targets(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
    search: str | None = Query(None, description="Search by name"),  # noqa: B008, RUF100
    target_type: str | None = Query(None, description="Filter by type"),  # noqa: B008, RUF100
) -> list[dict]:
    """List all targets with optional filters."""
    query = select(Target)
    if search:
        query = query.where(Target.name.ilike(f"%{search}%"))
    if target_type:
        query = query.where(Target.type == target_type)
    query = query.order_by(Target.name)
    targets = db.exec(query).all()  # type: ignore[union-attr]
    return [_to_response(t) for t in targets]


@router.get("/{target_id}", response_model=dict)
async def get_target(
    target_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Get a target by ID."""
    try:
        uid = UUID(target_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid target ID") from err

    target = db.get(Target, uid)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")
    return _to_response(target)


@router.post("", response_model=dict, status_code=201)
async def create_target(
    body: TargetCreateRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Create a new target."""
    target = Target(
        name=body.name,
        type=body.type,
        raw=body.raw,
        tags=body.tags or [],
        description=body.description,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return _to_response(target)


@router.put("/{target_id}", response_model=dict)
async def update_target(
    target_id: str,
    body: TargetUpdateRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Update a target."""
    try:
        uid = UUID(target_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid target ID") from err

    target = db.get(Target, uid)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(target, key, value)

    db.add(target)
    db.commit()
    db.refresh(target)
    return _to_response(target)


@router.delete("/{target_id}", response_model=dict)
async def delete_target(
    target_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Delete a target."""
    try:
        uid = UUID(target_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid target ID") from err

    target = db.get(Target, uid)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {target_id} not found")

    db.delete(target)
    db.commit()
    return {"status": "deleted", "id": target_id}
