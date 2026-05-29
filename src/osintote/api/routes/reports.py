# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado
# SPDX-License-Identifier: MIT
"""Reports API — generate and export OSINT reports.

Endpoints:
    POST   /api/reports               — Generate a report
    GET    /api/reports               — List generated reports
    GET    /api/reports/{id}/download — Download a report file
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/reports", tags=["Reports"])

REPORT_DIR = Path.home() / ".osintote" / "reports"


class ReportGenerateRequest(BaseModel):
    """Request body for generating a report."""

    task_id: str | None = None
    target_id: str | None = None
    format: str = "json"  # json, markdown, html


def _get_report_file(report_id: str) -> Path:
    """Get the path to a report file."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR / report_id


@router.get("", response_model=list[dict])
async def list_reports() -> list[dict]:
    """List all generated reports."""
    reports: list[dict] = []
    if not REPORT_DIR.is_dir():
        return reports

    for report_file in sorted(REPORT_DIR.glob("report-*.json"), reverse=True):
        try:
            data = json.loads(report_file.read_text(encoding="utf-8"))
            fmt = data.get("format", "json")
            ext = "md" if fmt == "markdown" else "html" if fmt == "html" else "json"
            reports.append({
                "id": report_file.stem.replace("report-", ""),
                "format": fmt,
                "filename": f"report-{report_file.stem.replace('report-', '')}.{ext}",
                "created_at": data.get("created_at"),
                "record_count": len(data.get("records", [])),
            })
        except Exception:
            pass

    return reports


@router.post("", response_model=dict, status_code=201)
async def generate_report(body: ReportGenerateRequest) -> dict:
    """Generate a report for a task or target."""
    report_id = str(uuid.uuid4())
    fmt = body.format.lower()
    if fmt not in ("json", "markdown", "html"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")

    # Build report data from raw records
    records: list[dict[str, Any]] = []

    report_data = {
        "id": report_id,
        "format": fmt,
        "task_id": body.task_id,
        "target_id": body.target_id,
        "created_at": datetime.now(UTC).isoformat(),
        "record_count": len(records),
        "records": records,
    }

    # Save report
    ext = "json" if fmt == "json" else "md" if fmt == "markdown" else "html"
    report_file = REPORT_DIR / f"report-{report_id}.{ext}"
    report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return {
        "id": report_id,
        "format": fmt,
        "filename": report_file.name,
        "record_count": len(records),
    }


@router.get("/{report_id}/download", response_model=dict)
async def download_report(report_id: str) -> dict:
    """Download a report file."""
    for ext in ("json", "md", "html"):
        report_file = REPORT_DIR / f"report-{report_id}.{ext}"
        if report_file.exists():
            return {
                "path": str(report_file),
                "filename": report_file.name,
            }

    raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
