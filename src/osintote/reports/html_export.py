# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""HTML report exporter.

Generates standalone HTML reports with:
- Embedded JSON data
- vis.js Network for relationship visualization
- Vanilla JS interactivity (filter, search, expand)
- Print CSS for paper-friendly output
- Dark/light theme toggle
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class HTMLExporter:
    """HTML report exporter.

    Produces standalone HTML reports with embedded data, vis.js
    network visualization, and vanilla JS interactivity.

    Parameters
    ----------
    data:
        Task data dictionary containing task info, records, and metadata.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize the HTML exporter."""
        self.data = data

    def render(self) -> str:
        """Render the HTML report.

        Returns
        -------
        str
            HTML-formatted report string.
        """
        task = self.data.get("task", {})
        records = self.data.get("records", [])
        metadata = self.data.get("metadata", {})
        summary = self._compute_summary(records)

        # Prepare data for vis.js
        vis_data = self._build_vis_data(records)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSINT Report — {task.get('name', 'Unknown')}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
            --info: #1f6feb;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 2rem; margin-bottom: 1rem; color: var(--text-primary); }}
        h2 {{ font-size: 1.5rem; margin: 2rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
        h3 {{ font-size: 1.2rem; margin: 1rem 0 0.5rem; }}
        .card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border: 1px solid var(--border);
        }}
        th {{ background: var(--bg-tertiary); color: var(--text-primary); }}
        td {{ color: var(--text-secondary); }}
        tr:hover td {{ background: var(--bg-tertiary); }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .badge-success {{ background: rgba(63,185,80,0.15); color: var(--success); }}
        .badge-warning {{ background: rgba(210,153,34,0.15); color: var(--warning); }}
        .badge-danger {{ background: rgba(248,81,73,0.15); color: var(--danger); }}
        .badge-info {{ background: rgba(31,111,235,0.15); color: var(--info); }}
        .risk-score {{
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
            margin: 1rem 0;
        }}
        .risk-high {{ color: var(--danger); }}
        .risk-moderate {{ color: var(--warning); }}
        .risk-low {{ color: var(--success); }}
        #network {{
            width: 100%;
            height: 400px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin: 1rem 0;
        }}
        .search-box {{
            width: 100%;
            padding: 0.75rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 1rem;
            margin-bottom: 1rem;
        }}
        .search-box:focus {{ outline: none; border-color: var(--accent); }}
        .filter-bar {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 0.5rem 1rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.9rem;
        }}
        .filter-btn:hover, .filter-btn.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }}
        .stat-card {{
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 6px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2rem; font-weight: 700; }}
        .stat-label {{ color: var(--text-secondary); font-size: 0.9rem; }}
        @media print {{
            body {{ background: #fff; color: #000; padding: 1rem; }}
            .card {{ border: 1px solid #ccc; }}
            th {{ background: #f5f5f5; }}
            .search-box, .filter-bar {{ display: none; }}
            #network {{ display: none; }}
            .badge {{ border: 1px solid #999; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 OSINT Report</h1>

        <div class="card">
            <h2>Task Information</h2>
            <table>
                <tr><th>Task ID</th><td><code>{task.get('id', 'N/A')}</code></td></tr>
                <tr><th>Name</th><td>{task.get('name', 'N/A')}</td></tr>
                <tr><th>Status</th><td><span class="badge badge-info">{task.get('status', 'N/A')}</span></td></tr>
                <tr><th>Recipe</th><td>{task.get('recipe', 'custom') or 'custom'}</td></tr>
                <tr><th>Created</th><td>{task.get('created_at', 'N/A')}</td></tr>
                <tr><th>Completed</th><td>{task.get('completed_at', 'N/A')}</td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Risk Assessment</h2>
            <div class="risk-score risk-{summary['risk_level']}">{summary['risk_score']}/10</div>
            <p style="text-align:center; color: var(--text-secondary);">
                {'HIGH' if summary['risk_level'] == 'high' else 'MODERATE' if summary['risk_level'] == 'moderate' else 'LOW'} Risk
            </p>
        </div>

        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{summary['total_records']}</div>
                <div class="stat-label">Total Records</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(summary['type_counts'])}</div>
                <div class="stat-label">Record Types</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(metadata.get('record_types', []))}</div>
                <div class="stat-label">Unique Types</div>
            </div>
        </div>

        <h2>Records</h2>
        <input type="text" class="search-box" id="searchInput" placeholder="Search records...">
        <div class="filter-bar" id="filterBar"></div>
        <table id="recordsTable">
            <thead>
                <tr><th>#</th><th>Type</th><th>Target</th><th>Data</th></tr>
            </thead>
            <tbody>
""" + "".join(
            f"""                <tr data-type="{r.get('type', 'unknown')}" data-target="{r.get('target', '')}">
                    <td>{i}</td>
                    <td><span class="badge badge-info">{r.get('type', 'unknown')}</span></td>
                    <td><code>{r.get('target', 'N/A')}</code></td>
                    <td>{self._format_record_data(r.get('data', {}))}</td>
                </tr>"""
            for i, r in enumerate(records, 1)
        ) + """
            </tbody>
        </table>

        <h2>Relationship Graph</h2>
        <div id="network"></div>

        <hr style="border-color: var(--border); margin: 2rem 0;">
        <p style="color: var(--text-secondary); font-size: 0.9rem;">
            Report generated from task <code>{task.get('id', 'unknown')}</code>
        </p>
    </div>

    <script>
        // Embed report data
        const REPORT_DATA = {json.dumps(self.data, default=str)};

        // Search functionality
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', filterTable);

        // Build filter buttons
        const typeCounts = {};
        REPORT_DATA.records.forEach(r => {{
            typeCounts[r.type] = (typeCounts[r.type] || 0) + 1;
        }});
        const filterBar = document.getElementById('filterBar');
        Object.keys(typeCounts).sort().forEach(type => {{
            const btn = document.createElement('button');
            btn.className = 'filter-btn';
            btn.textContent = `${{type}} (${typeCounts[type]})`;
            btn.onclick = () => toggleFilter(btn, type);
            filterBar.appendChild(btn);
        }});

        function filterTable() {{
            const query = searchInput.value.toLowerCase();
            document.querySelectorAll('#recordsTable tbody tr').forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            }});
        }}

        let activeFilter = null;
        function toggleFilter(btn, type) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            if (activeFilter === type) {{
                activeFilter = null;
                filterTable();
            }} else {{
                activeFilter = type;
                btn.classList.add('active');
                document.querySelectorAll('#recordsTable tbody tr').forEach(row => {{
                    row.style.display = row.dataset.type === type ? '' : 'none';
                }});
            }}
        }}

        // vis.js Network
        const visData = {json.dumps(vis_data, default=str)};
        if (visData.nodes.length > 0) {{
            const networkContainer = document.getElementById('network');
            const nodes = new visData.Network.DataSet(visData.nodes);
            const edges = new visData.Network.DataSet(visData.edges);
            const network = new visData.Network(networkContainer, {{ nodes, edges }}, {{
                physics: {{ stabilization: false }},
                interaction: {{ hover: true, zoomView: true }},
                layout: {{ randomSeed: 42 }},
            }});
        }}
    </script>
</body>
</html>"""

    def _compute_summary(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute summary statistics."""
        type_counts: dict[str, int] = {}
        for record in records:
            rtype = record.get("type", "unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

        # Simple risk scoring
        risk_indicators = {"ip": 1, "domain": 1, "http": 3, "dns": 1, "whois": 2, "port": 2, "vuln": 5}
        total_risk = sum(risk_indicators.get(rtype, 0) for rtype in type_counts)
        risk_score = min(10, total_risk)
        risk_level = "low" if risk_score < 5 else "moderate" if risk_score < 8 else "high"

        return {
            "total_records": len(records),
            "type_counts": type_counts,
            "risk_score": risk_score,
            "risk_level": risk_level,
        }

    def _format_record_data(self, data: Any) -> str:
        """Format record data for HTML display."""
        if isinstance(data, dict):
            items = []
            for k, v in list(data.items())[:5]:
                items.append(f"<b>{k}:</b> {v}")
            return ", ".join(items)
        return str(data)

    def _build_vis_data(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Build vis.js network data from records.

        Creates nodes (targets) and edges (relationships between targets
        and their records).
        """
        nodes = []
        edges = []
        node_id_map: dict[str, int] = {}
        next_id = 0

        for record in records:
            target = record.get("target", "")
            rtype = record.get("type", "unknown")
            if target not in node_id_map:
                node_id_map[target] = next_id
                nodes.append({
                    "id": next_id,
                    "label": target,
                    "shape": "dot",
                    "size": 20,
                    "color": {"background": "#58a6ff", "border": "#1f6feb"},
                    "title": f"Target: {target}",
                })
                next_id += 1

            record_id = next_id
            nodes.append({
                "id": next_id,
                "label": rtype,
                "shape": "box",
                "size": 15,
                "color": {"background": "#3fb950", "border": "#238636"},
                "title": f"Record type: {rtype}",
            })
            edges.append({
                "from": node_id_map[target],
                "to": record_id,
                "label": rtype,
            })
            next_id += 1

        return {"nodes": nodes, "edges": edges}
