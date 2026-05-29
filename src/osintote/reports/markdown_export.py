# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Markdown report exporter.

Generates human-readable Markdown reports with:
- Task metadata section
- Summary table with record type counts
- Risk score calculation
- Detailed records table
- Findings summary
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MarkdownExporter:
    """Markdown report exporter.

    Produces human-readable Markdown reports with tables, summary,
    risk score, and findings.

    Parameters
    ----------
    data:
        Task data dictionary containing task info, records, and metadata.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize the Markdown exporter."""
        self.data = data

    def render(self) -> str:
        """Render the Markdown report.

        Returns
        -------
        str
            Markdown-formatted report string.
        """
        lines = [
            "# OSINT Report",
            "",
            "## Task Summary",
            "",
            self._render_task_table(),
            "",
            "## Findings Summary",
            "",
            self._render_summary_section(),
            "",
            "## Risk Assessment",
            "",
            self._render_risk_score(),
            "",
            "## Records",
            "",
            self._render_records_table(),
            "",
            "---",
            "",
            f"*Report generated from task `{self.data.get('task', {}).get('id', 'unknown')}`*",
        ]
        return "\n".join(lines)

    def _render_task_table(self) -> str:
        """Render task metadata as a Markdown table."""
        task = self.data.get("task", {})
        lines = [
            "| Field | Value |",
            "|-------|-------|",
            f"| **Task ID** | `{task.get('id', 'N/A')}` |",
            f"| **Name** | {task.get('name', 'N/A')} |",
            f"| **Status** | {task.get('status', 'N/A')} |",
            f"| **Recipe** | {task.get('recipe', 'N/A') or 'custom'} |",
        ]
        if task.get("created_at"):
            lines.append(f"| **Started** | {task['created_at']} |")
        if task.get("completed_at"):
            lines.append(f"| **Completed** | {task['completed_at']} |")
        return "\n".join(lines)

    def _render_summary_section(self) -> str:
        """Render findings summary as a Markdown table."""
        records = self.data.get("records", [])

        # Count by type
        type_counts: dict[str, int] = {}
        for record in records:
            rtype = record.get("type", "unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

        lines = [
            f"**Total records found:** {len(records)}",
            "",
            "| Type | Count |",
            "|------|-------|",
        ]
        for rtype, count in sorted(type_counts.items()):
            lines.append(f"| {rtype} | {count} |")
        return "\n".join(lines)

    def _render_risk_score(self) -> str:
        """Calculate and render risk score."""
        metadata = self.data.get("metadata", {})
        record_types = metadata.get("record_types", [])

        # Simple risk scoring based on data types found
        risk_indicators = {
            "ip": 1,
            "domain": 1,
            "http": 3,
            "dns": 1,
            "whois": 2,
            "port": 2,
            "vuln": 5,
        }

        total_risk = 0
        for rtype in record_types:
            total_risk += risk_indicators.get(rtype, 0)

        # Normalize to 0-10 scale
        risk_score = min(10, total_risk)
        risk_level = self._risk_level(risk_score)

        lines = [
            f"**Risk Score: {risk_score}/10** ({risk_level})",
            "",
        ]
        if risk_score >= 8:
            lines.append(
                "> ⚠️ **HIGH RISK**: Significant exposure detected. "
                "Recommend immediate security review and hardening measures."
            )
        elif risk_score >= 5:
            lines.append(
                "> ⚠️ **MODERATE RISK**: Moderate exposure detected. "
                "Recommend security review and monitoring."
            )
        else:
            lines.append(
                "> ✅ **LOW RISK**: Minimal exposure detected. Continue standard monitoring."
            )
        return "\n".join(lines)

    def _risk_level(self, score: int) -> str:
        """Get risk level string from score."""
        if score >= 8:
            return "HIGH"
        elif score >= 5:
            return "MODERATE"
        return "LOW"

    def _render_records_table(self) -> str:
        """Render records as a Markdown table."""
        records = self.data.get("records", [])

        if not records:
            return "*No records found.*"

        lines = [
            "| # | Type | Target | Data |",
            "|---|------|--------|------|",
        ]

        for i, record in enumerate(records, 1):
            rtype = record.get("type", "unknown")
            target = record.get("target", "N/A")
            data = record.get("data", {})

            # Flatten data to a readable string
            data_str = ""
            if isinstance(data, dict):
                items = []
                for k, v in list(data.items())[:5]:  # Limit to first 5 keys
                    items.append(f"{k}: {v}")
                data_str = ", ".join(items)
                if len(data) > 5:
                    data_str += f" (+{len(data) - 5} more)"

            lines.append(f"| {i} | {rtype} | `{target}` | {data_str} |")

        return "\n".join(lines)
