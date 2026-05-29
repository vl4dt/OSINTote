# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""Settings CRUD API — project configuration key-value store.

Endpoints:
    GET    /api/settings              — List all settings
    GET    /api/settings/{key}        — Get a setting by key
    PUT    /api/settings/{key}        — Create or update a setting
    DELETE /api/settings/{key}        — Delete a setting
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from osintote.models.database import get_async_session
from osintote.models.orm import Setting

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingUpdateRequest(BaseModel):
    """Request body for setting create/update."""

    value: dict[str, Any]
    description: str | None = None


def _to_response(s: Setting) -> dict[str, Any]:
    """Convert a Setting ORM object to a dict."""
    return {
        "key": s.key,
        "value": s.value or {},
        "description": s.description,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("", response_model=list[dict])
async def list_settings(
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> list[dict]:
    """List all settings."""
    settings = db.exec(select(Setting).order_by(Setting.key)).all()  # type: ignore[union-attr]
    return [_to_response(s) for s in settings]


@router.get("/{key}", response_model=dict)
async def get_setting(
    key: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Get a setting by key."""
    setting = db.get(Setting, key)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    return _to_response(setting)


@router.put("/{key}", response_model=dict)
async def upsert_setting(
    key: str,
    body: SettingUpdateRequest,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Create or update a setting."""
    setting = db.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=body.value or {}, description=body.description)
        db.add(setting)
    else:
        if body.value is not None:
            setting.value = body.value
        if body.description is not None:
            setting.description = body.description

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return _to_response(setting)


@router.delete("/{key}", response_model=dict)
async def delete_setting(
    key: str,
    db: Session = Depends(get_async_session),  # noqa: B008, RUF100
) -> dict:
    """Delete a setting."""
    setting = db.get(Setting, key)
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")

    db.delete(setting)
    db.commit()
    return {"status": "deleted", "key": key}
