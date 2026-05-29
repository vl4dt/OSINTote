# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI workflow suggestion system — post-task recommendation engine.

Provides:
    - Rule-based critical finding detection (exposed DB, admin panels, SSH,
      default credentials, open ports)
    - Auto-queue follow-up tasks on critical match
    - AI-powered recommendations via provider integration

Usage::

    from osintote.ai.suggester import Suggester, FindingSuggestion

    suggester = Suggester()
    suggestions = suggester.generate(records, target)
    for s in suggestions:
        print(f"  [{s.severity}] {s.description}")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .provider import AIProviderRegistry

logger = logging.getLogger(__name__)


# ── Suggestion model ────────────────────────────────────────────────────


@dataclass
class FindingSuggestion:
    """A single workflow suggestion.

    Attributes
    ----------
    finding_type:
        Category of the finding (e.g., "exposed_db", "admin_panel").
    severity:
        Severity level (critical/high/medium/low/info).
    description:
        Human-readable description.
    recommended_actions:
        List of suggested follow-up actions.
    auto_queue:
        Whether to automatically queue a follow-up task.
    """

    finding_type: str
    severity: str
    description: str
    recommended_actions: list[str] = field(default_factory=list)
    auto_queue: bool = False


# ── Pattern definitions ─────────────────────────────────────────────────

CRITICAL_FINDING_PATTERNS: dict[str, dict[str, Any]] = {
    "exposed_database": {
        "finding_type": "exposed_db",
        "severity": "critical",
        "description": "Database service exposed on network port",
        "patterns": [
            re.compile(r"mysql|postgres|mssql|mariadb|mongodb|redis|rdbms", re.IGNORECASE),
            re.compile(r"port\s*[=:]\s*(3306|5432|1433|27017|6379|9200)", re.IGNORECASE),
        ],
        "actions": [
            "Verify database is not accessible from public internet",
            "Check for default credentials",
            "Scan for known database vulnerabilities",
        ],
        "auto_queue": True,
    },
    "exposed_admin": {
        "finding_type": "exposed_admin",
        "severity": "high",
        "description": "Administrative interface detected",
        "patterns": [
            re.compile(r"admin|dashboard|panel|cpanel|webmail|phpmyadmin|wp-admin", re.IGNORECASE),
            re.compile(r"login|auth|console", re.IGNORECASE),
        ],
        "actions": [
            "Check for weak/default authentication",
            "Verify admin access is restricted",
            "Look for admin panel information disclosure",
        ],
        "auto_queue": True,
    },
    "open_ssh": {
        "finding_type": "open_ssh",
        "severity": "medium",
        "description": "SSH service detected on target",
        "patterns": [
            re.compile(r"ssh|openssh|secsh", re.IGNORECASE),
            re.compile(r"port\s*[=:]\s*22", re.IGNORECASE),
        ],
        "actions": [
            "Check SSH version for known vulnerabilities",
            "Verify SSH configuration (root login, password auth)",
            "Consider SSH key-based authentication only",
        ],
        "auto_queue": True,
    },
    "default_credentials": {
        "finding_type": "default_creds",
        "severity": "critical",
        "description": "Default or weak credentials detected",
        "patterns": [
            re.compile(r"admin:admin|root:root|test:test|guest:guest", re.IGNORECASE),
            re.compile(r"default|weak|password", re.IGNORECASE),
        ],
        "actions": [
            "Immediately change default credentials",
            "Implement account lockout policies",
            "Enable multi-factor authentication",
        ],
        "auto_queue": True,
    },
    "open_rdp": {
        "finding_type": "open_rdp",
        "severity": "high",
        "description": "RDP service exposed on network",
        "patterns": [
            re.compile(r"rdp|terminal|windows\s*remote", re.IGNORECASE),
            re.compile(r"port\s*[=:]\s*3389", re.IGNORECASE),
        ],
        "actions": [
            "Restrict RDP access to VPN only",
            "Enable Network Level Authentication (NLA)",
            "Check for BlueKeep and similar CVEs",
        ],
        "auto_queue": True,
    },
    "exposed_file_service": {
        "finding_type": "exposed_file_service",
        "severity": "high",
        "description": "File sharing service exposed",
        "patterns": [
            re.compile(r"smb|samba|nfs|ftp|sftp|webdav", re.IGNORECASE),
            re.compile(r"port\s*[=:]\s*(21|445|139|2049|873)", re.IGNORECASE),
        ],
        "actions": [
            "Restrict file service access to authorized networks",
            "Check for anonymous access",
            "Verify SMB signing is enabled",
        ],
        "auto_queue": True,
    },
}


# ── Suggester ───────────────────────────────────────────────────────────


class Suggester:
    """Workflow suggestion engine for OSINT findings.

    Combines rule-based critical finding detection with optional
    AI-powered recommendations.

    Parameters
    ----------
    registry:
        AI provider registry (optional for AI-powered suggestions).
    """

    def __init__(
        self,
        registry: AIProviderRegistry | None = None,
    ) -> None:
        """Initialize the suggester.

        Parameters
        ----------
        registry:
            AI provider registry for AI-powered suggestions.
            If not provided, only rule-based suggestions are returned.
        """
        self.registry = registry

    def generate(
        self,
        records: list[dict[str, Any]],
        target: str,
        use_ai: bool = True,
    ) -> list[FindingSuggestion]:
        """Generate workflow suggestions for a set of findings.

        Applies rule-based detection first, then optionally augments
        with AI-powered suggestions.

        Parameters
        ----------
        records:
            List of finding records.
        target:
            Target identifier.
        use_ai:
            If True and registry is configured, augment with AI suggestions.

        Returns
        -------
        list[FindingSuggestion]
            List of structured suggestions.
        """
        suggestions: list[FindingSuggestion] = []
        detected_types: set[str] = set()

        # Step 1: Rule-based detection
        for pattern_key, pattern_config in CRITICAL_FINDING_PATTERNS.items():
            if pattern_key in detected_types:
                continue

            for record in records:
                text = self._extract_text(record)
                for pat in pattern_config["patterns"]:
                    if pat.search(text):
                        suggestion = FindingSuggestion(
                            finding_type=pattern_config["finding_type"],
                            severity=pattern_config["severity"],
                            description=pattern_config["description"],
                            recommended_actions=pattern_config["actions"],
                            auto_queue=pattern_config["auto_queue"],
                        )
                        suggestions.append(suggestion)
                        detected_types.add(pattern_key)
                        break
            else:
                continue
            break  # Only need one match per pattern

        # Step 2: AI-powered suggestions (optional)
        if use_ai and self.registry and self.registry.is_enabled:
            ai_suggestions = self._get_ai_suggestions(records, target)
            if ai_suggestions:
                for text in ai_suggestions[:5]:
                    suggestions.append(
                        FindingSuggestion(
                            finding_type="ai_recommendation",
                            severity="info",
                            description=text,
                            recommended_actions=[text],
                        )
                    )

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        suggestions.sort(key=lambda s: severity_order.get(s.severity, 4))

        return suggestions

    def detect_critical(self, records: list[dict[str, Any]]) -> list[FindingSuggestion]:
        """Detect only critical/high severity findings.

        Parameters
        ----------
        records:
            List of finding records.

        Returns
        -------
        list[FindingSuggestion]
            Only critical and high severity findings.
        """
        all_suggestions = self.generate(records, target="unknown", use_ai=False)
        return [s for s in all_suggestions if s.severity in ("critical", "high")]

    def _extract_text(self, record: dict[str, Any]) -> str:
        """Extract searchable text from a finding record."""
        parts = [
            record.get("message", ""),
            record.get("type", ""),
            record.get("target", ""),
            str(record.get("data", "")),
        ]
        return " ".join(parts)

    async def _get_ai_suggestions(
        self,
        records: list[dict[str, Any]],
        target: str,
    ) -> list[str]:
        """Get AI-powered suggestions.

        Parameters
        ----------
        records:
            Finding records.
        target:
            Target identifier.

        Returns
        -------
        list[str]
            AI-generated recommendation strings.
        """
        # Build context summary
        context_lines: list[str] = []
        for rec in records[:50]:
            type_ = rec.get("type", "unknown")
            data = rec.get("data", {})
            if isinstance(data, dict):
                severity = data.get("severity", "info")
                context_lines.append(f"[{severity}] {type_}: {data.get('message', rec.get('message', ''))}")  # noqa: E501
            else:
                context_lines.append(f"{type_}: {data!s}")

        context = "\n".join(context_lines)
        suggestions = await self.registry.suggest(context, target)
        return suggestions

    @staticmethod
    def has_critical_findings(records: list[dict[str, Any]]) -> bool:
        """Check if records contain critical/high severity findings.

        Parameters
        ----------
        records:
            Finding records.

        Returns
        -------
        bool
            True if critical or high severity findings exist.
        """
        for rec in records:
            sev = rec.get("data", {}).get("severity", "info")
            if sev in ("critical", "high"):
                return True
        return False
