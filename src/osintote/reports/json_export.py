# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""JSON report exporter.

Generates structured JSON reports with task metadata, records, and
summary statistics.

Example output::

    {
      "task": {
        "id": "uuid",
        "name": "Task Name",
        "status": "completed",
        ...
      },
      "records": [...],
      "summary": {
        "total_records": 42,
        "record_types": ["dns", "http"],
        ...
      }
    }
"""

from __future__ import annotations

import json
from typing import Any


class JSONExporter:
    """JSON report exporter.

    Produces structured JSON reports with task metadata, records,
    and summary statistics.

    Parameters
    ----------
    data:
        Task data dictionary containing task info, records, and metadata.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize the JSON exporter."""
        self.data = data

    def render(self) -> str:
        """Render the JSON report.

        Returns
        -------
        str
            JSON-formatted report string.
        """
        enriched = self._enrich_data(self.data)
        return json.dumps(enriched, indent=2, default=str)

    def _enrich_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Enrich task data with computed summary fields.

        Parameters
        ----------
        data:
            Raw task data.

        Returns
        -------
        dict
            Enriched task data with summary fields.
        """
        records = data.get("records", [])

        # Count records by type
        type_counts: dict[str, int] = {}
        for record in records:
            rtype = record.get("type", "unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

        # Compute summary statistics
        summary = {
            "total_records": len(records),
            "record_types": list(type_counts.keys()),
            "type_counts": type_counts,
            "task_status": data.get("task", {}).get("status", "unknown"),
            "task_name": data.get("task", {}).get("name", ""),
            "generated_at": "now",
        }

        return {
            "task": data.get("task", {}),
            "records": records,
            "summary": summary,
        }
