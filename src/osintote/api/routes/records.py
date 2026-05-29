# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""Records/Results CRUD API — list and query OSINT records.

Endpoints:
    GET    /api/records               — List all records
    GET    /api/records/{id}          — Get record details
    GET    /api/records?target_id=xxx — Filter records by target
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from osintote.models.database import get_async_session
from osintote.models.orm import Record, RecordType, Target

router = APIRouter(prefix="/api/records", tags=["Records"])


class RecordCreateRequest(BaseModel):
    """Request body for creating a record."""

    target_id: str
    type: str
    source: str
    data: dict[str, Any] = {}
    confidence: float = 1.0
    metadata_: dict[str, Any] = {}


def _to_response(r: Record) -> dict[str, Any]:
    """Convert a Record ORM object to a dict."""
    return {
        "id": str(r.id),
        "target_id": str(r.target_id),
        "type": r.type.value if hasattr(r.type, "value") else str(r.type),
        "source": r.source,
        "data": r.data or {},
        "metadata": r.metadata_ or {},
        "confidence": r.confidence,
        "target_name": r.target.name if hasattr(r, "target") and r.target else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("", response_model=list[dict])
async def list_records(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
    target_id: str | None = Query(None, description="Filter by target ID"),  # noqa: B008, RUF100
    record_type: str | None = Query(None, description="Filter by record type"),  # noqa: B008, RUF100
    source: str | None = Query(None, description="Filter by source"),  # noqa: B008, RUF100
    severity: str | None = Query(None, description="Filter by severity"),  # noqa: B008, RUF100
    limit: int = 500,
    offset: int = 0,
) -> list[dict]:
    """List all records with optional filters."""
    query = select(Record)

    if target_id:
        try:
            query = query.where(Record.target_id == UUID(target_id))
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Invalid target_id") from err

    if record_type:
        query = query.where(Record.type == record_type)

    if source:
        query = query.where(Record.source == source)

    if severity:
        confidence_map = {
            "critical": (0.9, 1.0),
            "high": (0.7, 0.9),
            "medium": (0.4, 0.7),
            "low": (0.1, 0.4),
            "info": (0.0, 0.1),
        }
        if severity in confidence_map:
            low, high = confidence_map[severity]
            query = query.where(Record.confidence >= low * 100, Record.confidence < high * 100)

    query = query.order_by(Record.created_at.desc()).limit(limit).offset(offset)
    records = db.exec(query).all()  # type: ignore[union-attr]
    return [_to_response(r) for r in records]


@router.get("/{record_id}", response_model=dict)
async def get_record(
    record_id: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Get a record by ID."""
    try:
        uid = UUID(record_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid record ID") from err

    record = db.get(Record, uid)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return _to_response(record)


@router.post("", response_model=dict, status_code=201)
async def create_record(
    body: RecordCreateRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Create a new record."""
    try:
        target_uid = UUID(body.target_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid target_id") from err

    # Verify target exists
    target = db.get(Target, target_uid)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Target {body.target_id} not found")

    record = Record(
        target_id=target_uid,
        type=RecordType(body.type),
        source=body.source,
        data=body.data or {},
        confidence=body.confidence,
        metadata_=body.metadata_ or {},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_response(record)
