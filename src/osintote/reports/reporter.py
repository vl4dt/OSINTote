# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Report generation service — multi-format report export.

Coordinates JSON, Markdown, and HTML report generation from task data.
Provides a unified interface for generating reports in multiple formats.

Example::

    from osintote.reports import Reporter, ReportFormat

    reporter = Reporter(task_id=task_id)
    json_report = reporter.generate(ReportFormat.JSON)
    md_report = reporter.generate(ReportFormat.MARKDOWN)
    html_report = reporter.generate(ReportFormat.HTML)
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Supported report export formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class Reporter:
    """Report generation service.

    Generates reports in multiple formats from task and record data.
    Uses exporter classes (JSONExporter, MarkdownExporter, HTMLExporter)
    to produce format-specific output.

    Parameters
    ----------
    task_id:
        UUID of the task to generate a report for.
    output_dir:
        Directory to write exported files to (default: .osintote/reports/).
    """

    def __init__(self, task_id: UUID, output_dir: Path | None = None) -> None:
        """Initialize the reporter."""
        self.task_id = task_id
        self.output_dir = output_dir or Path(".osintote/reports/")
        self._exporters: dict[ReportFormat, Any] = {}

    def generate(self, fmt: ReportFormat) -> str:
        """Generate a report in the specified format.

        Parameters
        ----------
        fmt:
            Report format to generate.

        Returns
        -------
        str
            Generated report content.
        """
        data = self._collect_task_data()

        if fmt == ReportFormat.JSON:
            return self._generate_json(data)
        elif fmt == ReportFormat.MARKDOWN:
            return self._generate_markdown(data)
        elif fmt == ReportFormat.HTML:
            return self._generate_html(data)

        raise ValueError(f"Unsupported format: {fmt}")

    def export(self, fmt: ReportFormat, filename: str | None = None) -> Path:
        """Generate and save a report to a file.

        Parameters
        ----------
        fmt:
            Report format to generate.
        filename:
            Output filename (default: generated from task_id and format).

        Returns
        -------
        Path
            Path to the generated report file.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            suffixes = {
                ReportFormat.JSON: ".json",
                ReportFormat.MARKDOWN: ".md",
                ReportFormat.HTML: ".html",
            }
            filename = f"report-{self.task_id.hex()}{suffixes[fmt]}"

        filepath = self.output_dir / filename
        content = self.generate(fmt)
        filepath.write_text(content, encoding="utf-8")
        logger.info("Report exported: %s (%s)", filepath, fmt.value)
        return filepath

    def generate_all(self, filename_prefix: str = "report") -> dict[ReportFormat, Path]:
        """Generate reports in all formats.

        Parameters
        ----------
        filename_prefix:
            Filename prefix for generated files.

        Returns
        -------
        dict
            Mapping of ReportFormat → Path for each generated report.
        """
        results: dict[ReportFormat, Path] = {}
        for fmt in ReportFormat:
            fname = f"{filename_prefix}-{fmt.value}.html" if fmt == ReportFormat.HTML else f"{filename_prefix}-{fmt.value}"
            results[fmt] = self.export(fmt, filename=fname)
        return results

    def _collect_task_data(self) -> dict[str, Any]:
        """Collect task and record data from the database.

        Returns
        -------
        dict
            Task data including task info, records, and metadata.
        """
        # Import here to avoid circular imports
        from osintote.models.database import get_session
        from osintote.models.orm import Record, Task
        from sqlmodel import select

        with get_session() as session:
            task = session.get(Task, self.task_id)
            if task is None:
                raise ValueError(f"Task {self.task_id} not found")

            records_stmt = select(Record).where(Record.task_id == self.task_id)
            records = session.exec(records_stmt).all()

            return {
                "task": {
                    "id": str(task.id),
                    "name": task.name,
                    "status": task.status.value if task.status else "unknown",
                    "created_at": str(task.created_at) if task.created_at else "",
                    "completed_at": str(task.completed_at) if task.completed_at else "",
                    "recipe": task.recipe_name or "",
                },
                "records": [
                    {
                        "id": str(r.id),
                        "type": r.record_type.value if r.record_type else "",
                        "target": r.target or "",
                        "data": json.loads(r.data) if r.data else {},
                        "created_at": str(r.created_at) if r.created_at else "",
                    }
                    for r in records
                ],
                "metadata": {
                    "total_records": len(records),
                    "record_types": list(set(r.record_type.value for r in records if r.record_type)),
                },
            }

    def _generate_json(self, data: dict[str, Any]) -> str:
        """Generate JSON report."""
        return json.dumps(data, indent=2, default=str)

    def _generate_markdown(self, data: dict[str, Any]) -> str:
        """Generate Markdown report."""
        from osintote.reports.markdown_export import MarkdownExporter

        exporter = MarkdownExporter(data)
        return exporter.render()

    def _generate_html(self, data: dict[str, Any]) -> str:
        """Generate HTML report."""
        from osintote.reports.html_export import HTMLExporter

        exporter = HTMLExporter(data)
        return exporter.render()
