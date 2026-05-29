# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Context pruning system — auto-summarizer for OSINT findings.

Prunes and summarizes OSINT findings to fit within context windows
for downstream AI analysis. Provides:

- Rule-based summarization with configurable limits
- Deduplication of similar findings
- Severity-based filtering
- Token-budget-aware truncation
- Statistical summaries (counts, distributions)
- JSON and text output formats

Example::

    from osintote.engine.context_pruning import ContextPruner

    pruner = ContextPruner(max_tokens=4000)
    summary = pruner.summarize(records)
    # Returns pruned findings with stats
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────


@dataclass
class PruningConfig:
    """Configuration for context pruning."""

    max_tokens: int = 4000
    max_records: int = 500
    max_records_per_type: int = 100
    dedup_similar: bool = True
    min_severity: str = "low"  # Filter below this severity
    include_metadata: bool = True
    max_summary_length: int = 200  # Max chars per summary string


# ── Result ──────────────────────────────────────────────────────────────────


@dataclass
class PrunedContext:
    """Pruned context ready for AI analysis.

    Attributes
    ----------
    records:
        Pruned and deduplicated findings.
    summary:
        Human-readable summary of the findings.
    stats:
        Statistical summary (counts, distributions).
    metadata_:
        Extra metadata (pruning config, token count).
    """

    records: list[dict[str, Any]]
    summary: str
    stats: dict[str, Any]
    metadata_: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return {
            "records": self.records,
            "summary": self.summary,
            "stats": self.stats,
            "metadata": self.metadata_,
        }

    def to_text(self) -> str:
        """Serialize to a plain text summary."""
        lines = [self.summary, ""]
        for rec in self.records[:50]:
            lines.append(f"  [{rec.get('type', 'unknown')}] {rec.get('target', '?')}")
            data = rec.get("data", {})
            if isinstance(data, dict):
                for k, v in list(data.items())[:3]:
                    lines.append(f"    {k}: {v}")
        return "\n".join(lines)


# ── Pruner ──────────────────────────────────────────────────────────────────


class ContextPruner:
    """Context pruning system for OSINT findings.

    Prunes and summarizes findings to fit within AI context windows.
    Applies deduplication, severity filtering, and token-budget-aware
    truncation.

    Parameters
    ----------
    max_tokens:
        Maximum token budget (estimates ~4 chars per token).
    max_records:
        Maximum total records to retain.
    max_records_per_type:
        Maximum records per finding type.
    dedup_similar:
        Enable deduplication of similar findings.
    min_severity:
        Minimum severity level to include (low/medium/high/critical).
    max_summary_length:
        Maximum characters per summary string.
    """

    SEVERITY_ORDER: dict[str, int] = {
        "info": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def __init__(
        self,
        max_tokens: int = 4000,
        max_records: int = 500,
        max_records_per_type: int = 100,
        dedup_similar: bool = True,
        min_severity: str = "low",
        include_metadata: bool = True,
        max_summary_length: int = 200,
    ) -> None:
        """Initialize the context pruner."""
        self.config = PruningConfig(
            max_tokens=max_tokens,
            max_records=max_records,
            max_records_per_type=max_records_per_type,
            dedup_similar=dedup_similar,
            min_severity=min_severity,
            include_metadata=include_metadata,
            max_summary_length=max_summary_length,
        )

    def summarize(self, records: list[dict[str, Any]]) -> PrunedContext:
        """Prune and summarize a list of records.

        Applies deduplication, severity filtering, and truncation
        to fit within the configured token budget.

        Parameters
        ----------
        records:
            List of finding records to prune.

        Returns
        -------
        PrunedContext
            Pruned findings with summary and statistics.
        """
        # Step 1: Severity filtering
        filtered = self._filter_severity(records)

        # Step 2: Deduplication
        if self.config.dedup_similar:
            deduped = self._dedup(filtered)
        else:
            deduped = filtered

        # Step 3: Type-based limiting
        limited = self._limit_by_type(deduped)

        # Step 4: Token-budget truncation
        pruned = self._truncate_by_tokens(limited)

        # Step 5: Build summary and stats
        summary = self._build_summary(pruned, len(records))
        stats = self._compute_stats(pruned, len(records))

        metadata: dict[str, Any] = {}
        if self.config.include_metadata:
            metadata = {
                "max_tokens": self.config.max_tokens,
                "max_records": self.config.max_records,
                "max_records_per_type": self.config.max_records_per_type,
                "original_count": len(records),
                "pruned_count": len(pruned),
                "reduction_pct": round((1 - len(pruned) / max(len(records), 1)) * 100, 1),
            }

        return PrunedContext(
            records=pruned,
            summary=summary,
            stats=stats,
            metadata_=metadata,
        )

    def _filter_severity(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter records by minimum severity level."""
        min_level = self.SEVERITY_ORDER.get(self.config.min_severity, 0)
        return [
            rec for rec in records
            if self.SEVERITY_ORDER.get(rec.get("data", {}).get("severity", "info"), 0) >= min_level
        ]

    def _dedup(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate similar records based on type and key data."""
        seen: dict[str, int] = {}
        result: list[dict[str, Any]] = []

        for rec in records:
            # Create a hash based on type and key fields
            data = rec.get("data", {})
            if isinstance(data, dict):
                key_parts = [rec.get("type", ""), rec.get("target", "")]
                # Hash the most important fields
                for key in ["record_type", "address", "subdomain", "engine", "vulnerability", "product"]:
                    val = data.get(key)
                    if val is not None:
                        key_parts.append(str(val))
                key = hashlib.md5("".join(key_parts).encode()).hexdigest()[:16]
            else:
                key = hashlib.md5(str(rec).encode()).hexdigest()[:16]

            if key not in seen:
                seen[key] = len(result)
                result.append(rec)

        return result

    def _limit_by_type(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Limit records per type to configured max."""
        type_counts: dict[str, int] = {}
        result: list[dict[str, Any]] = []

        for rec in records:
            rtype = rec.get("type", "unknown")
            if type_counts.get(rtype, 0) < self.config.max_records_per_type:
                type_counts[rtype] = type_counts.get(rtype, 0) + 1
                result.append(rec)

        return result[: self.config.max_records]

    def _truncate_by_tokens(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Truncate records to fit within token budget."""
        max_chars = self.config.max_tokens * 4  # ~4 chars per token
        result: list[dict[str, Any]] = []
        total_chars = 0

        for rec in records:
            rec_str = str(rec)
            if total_chars + len(rec_str) <= max_chars:
                result.append(rec)
                total_chars += len(rec_str)
            else:
                # Partial inclusion - add a truncation note
                result.append({
                    "type": "pruning-note",
                    "target": "",
                    "data": {
                        "record_type": "Truncation",
                        "message": f"... ({len(records) - len(result)} more records pruned)",
                    },
                })
                break

        return result

    def _build_summary(self, records: list[dict[str, Any]], original_count: int) -> str:
        """Build a human-readable summary of the findings."""
        type_counts: dict[str, int] = {}
        for rec in records:
            rtype = rec.get("type", "unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

        # Sort by count descending
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        type_str = ", ".join(f"{count} {dtype}" for dtype, count in top_types)

        # Unique targets
        targets = set(rec.get("target", "") for rec in records if rec.get("target"))
        unique_targets = len(targets)

        return (
            f"Pruned context: {len(records)} records from {original_count} original "
            f"({original_count - len(records)} removed). "
            f"{unique_targets} unique targets. Top types: {type_str}."
        )

    def _compute_stats(self, records: list[dict[str, Any]], original_count: int) -> dict[str, Any]:
        """Compute statistical summary of the findings."""
        type_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        targets: set[str] = set()

        for rec in records:
            rtype = rec.get("type", "unknown")
            type_counts[rtype] = type_counts.get(rtype, 0) + 1

            sev = rec.get("data", {}).get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            target = rec.get("target", "")
            if target:
                targets.add(target)

        return {
            "total_records": len(records),
            "original_records": original_count,
            "unique_targets": len(targets),
            "types": type_counts,
            "severities": severity_counts,
        }


# ── Helper Functions ────────────────────────────────────────────────────────


def compute_token_estimate(text: str) -> int:
    """Estimate the number of tokens in a text string.

    Uses a simple heuristic: ~4 characters per token.

    Parameters
    ----------
    text:
        Input text to estimate.

    Returns
    -------
    int
        Estimated token count.
    """
    return max(1, len(text) // 4)


def is_within_budget(text: str, max_tokens: int) -> bool:
    """Check if text fits within the token budget.

    Parameters
    ----------
    text:
        Input text.
    max_tokens:
        Maximum token budget.

    Returns
    -------
    bool
        True if text fits within budget.
    """
    return compute_token_estimate(text) <= max_tokens


def truncate_text(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token budget.

    Parameters
    ----------
    text:
        Input text.
    max_tokens:
        Maximum token budget.

    Returns
    -------
    str
        Truncated text.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."
