# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Report generation service.

Exporters:
    JSON — structured report data (always available)
    Markdown — human-readable with tables, summary, risk score
    HTML — standalone with embedded data, vis.js + vanilla JS, print CSS
"""

from osintote.reports.json_export import JSONExporter
from osintote.reports.markdown_export import MarkdownExporter
from osintote.reports.reporter import Reporter, ReportFormat

__all__ = ["JSONExporter", "MarkdownExporter", "ReportFormat", "Reporter"]
