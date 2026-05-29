# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""AI analysis engine — post-task async analysis with structured output.

Provides:
    - Async post-task analysis via registered providers
    - Structured output: risk_score, summary, findings array
      (severity, evidence, recommendation), missing_data
    - Automatic prompt generation from task context
    - Integration with context pruner for token-efficient analysis

Usage::

    from osintote.ai.analysis_engine import AnalysisEngine

    engine = AnalysisEngine(registry)
    result = await engine.analyze(task_id, records)
    print(result.summary.risk_score)
    for finding in result.summary.findings:
        print(f"  {finding['severity']}: {finding['recommendation']}")
"""

from __future__ import annotations

import logging
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from ..engine.config import AIClientConfig
from ..engine.context_pruning import ContextPruner
from ..models.orm import ErrorSeverity, TaskStatus
from .models import AISummary, AIAnalysisResult
from .provider import AIProviderRegistry, AIClientConfig as ClientConfig

logger = logging.getLogger(__name__)

# ── Analysis result ─────────────────────────────────────────────────────


@dataclass
class AnalysisResult:
    """Result of an AI analysis.

    Attributes
    ----------
    summary:
        Structured AI summary (risk_score, summary, findings, etc.).
    raw:
        Raw response content for debugging.
    model_used:
        Model identifier used.
    task_id:
        Associated task ID.
    created_at:
        Analysis timestamp.
    """

    summary: AISummary
    raw: str = ""
    model_used: str = ""
    task_id: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict (JSON-safe)."""
        return {
            "summary": self.summary.model_dump(mode="python"),
            "raw": self.raw,
            "model_used": self.model_used,
            "task_id": self.task_id,
            "created_at": self.created_at,
        }


# ── Prompt builder ─────────────────────────────────────────────────────


class PromptBuilder:
    """Build analysis prompts from task context.

    Combines the task definition, pruned findings context, and
    target information into a structured analysis prompt.
    """

    SYSTEM_PROMPT = (
        "You are an experienced OSINT analyst. Analyze the findings "
        "below and provide a structured assessment.\n\n"
        "Return a valid JSON object with these fields:\n"
        "  - risk_score: number 0.0-10.0 (0=low risk, 10=critical)\n"
        "  - summary: brief executive summary of key findings\n"
        "  - findings: array of objects with:\n"
        "      severity: 'critical'|'high'|'medium'|'low'|'info'\n"
        "      category: brief category name\n"
        "      evidence: key evidence from the findings\n"
        "      recommendation: actionable recommendation\n"
        "  - recommendations: array of 2-5 high-level recommendations\n"
        "  - missing_data: array of data gaps that limit analysis\n\n"
        "IMPORTANT: Return ONLY valid JSON, no markdown, no explanation."
    )

    @staticmethod
    def build(
        target: str,
        pruned_context: dict[str, Any],
        task_type: str = "",
    ) -> tuple[str, str]:
        """Build an analysis prompt and system prompt.

        Parameters
        ----------
        target:
            Target identifier.
        pruned_context:
            Pruned context dict (from ContextPruner).
        task_type:
            Task/recon type.

        Returns
        -------
        tuple[str, str]
            (user_prompt, system_prompt)
        """
        context = pruned_context.get("records", [])
        stats = pruned_context.get("stats", {})
        context_summary = pruned_context.get("summary", "")

        # Build user prompt
        lines = [
            f"Target: {target}",
            f"Task type: {task_type or 'recon'}",
            "",
            f"Context summary: {context_summary}",
            "",
            f"Statistics:",
            f"  Total records: {stats.get('total_records', 0)}",
            f"  Unique targets: {stats.get('unique_targets', 0)}",
            f"  Types: {stats.get('types', {})}",
            f"  Severities: {stats.get('severities', {})}",
            "",
            "Findings:",
        ]

        for rec in context[:100]:
            rec_type = rec.get("type", "unknown")
            data = rec.get("data", {})
            target_field = rec.get("target", "")
            if isinstance(data, dict):
                sev = data.get("severity", "info")
                msg = data.get("message", data.get("record_type", ""))
                lines.append(f"  [{sev}] {rec_type}: {msg} ({target_field})")
            else:
                lines.append(f"  {rec_type}: {data}")

        user_prompt = "\n".join(lines)
        return user_prompt, PromptBuilder.SYSTEM_PROMPT


# ── Analysis engine ─────────────────────────────────────────────────────


class AnalysisEngine:
    """Async post-task analysis engine.

    Integrates with the AI provider registry to analyze OSINT findings
    after task completion. Uses context pruning for token efficiency.

    Parameters
    ----------
    registry:
        AI provider registry.
    config:
        Optional analysis config override.
    """

    def __init__(
        self,
        registry: AIProviderRegistry,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the analysis engine.

        Parameters
        ----------
        registry:
            AI provider registry.
        config:
            Optional config override (max_tokens, etc.).
        """
        self.registry = registry
        self.config = config or {}
        self.pruner = ContextPruner(
            max_tokens=self.config.get("max_tokens", 4000),
            max_records=self.config.get("max_records", 500),
        )

    async def analyze(
        self,
        target: str,
        records: list[dict[str, Any]],
        task_type: str = "",
        task_id: str | None = None,
    ) -> AnalysisResult:
        """Run AI analysis on a set of findings.

        Parameters
        ----------
        target:
            Target identifier.
        records:
            List of finding records.
        task_type:
            Recon task type.
        task_id:
            Associated task ID.

        Returns
        -------
        AnalysisResult
            Structured analysis result.
        """
        if not self.registry.is_enabled:
            return AnalysisResult(
                summary=AISummary(summary="AI analysis disabled"),
                task_id=task_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        # Step 1: Prune context
        pruned = self.pruner.summarize(records)
        pruned_dict = pruned.to_dict()

        # Step 2: Build prompt
        user_prompt, system_prompt = PromptBuilder.build(
            target=target,
            pruned_context=pruned_dict,
            task_type=task_type,
        )

        # Step 3: Run AI analysis
        logger.info("Running AI analysis for %s (%d records)", target, len(records))
        result = await self.registry.analyze(user_prompt, system_prompt)

        # Step 4: Parse structured output
        summary = self._parse_analysis_result(result)

        return AnalysisResult(
            summary=summary,
            raw=str(result),
            model_used=self.registry.config.model if self.registry.config else "",
            task_id=task_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def analyze_task(
        self,
        session: Session,
        task_id: str,
    ) -> AnalysisResult:
        """Run AI analysis on a completed task from the database.

        Parameters
        ----------
        session:
            Database session.
        task_id:
            Task UUID (string).

        Returns
        -------
        AnalysisResult
            Structured analysis result.
        """
        from ..models.orm import Record

        uid = uuid_module.UUID(task_id)
        task = session.get(Task, uid)
        if task is None:
            return AnalysisResult(
                summary=AISummary(summary=f"Task {task_id} not found"),
                task_id=task_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        stmt = select(Record).where(Record.task_id == uid)
        records = [r.model_dump(mode="python") for r in session.exec(stmt).all()]

        target_name = task.target_name if hasattr(task, "target_name") else ""
        if not target_name:
            from ..models.orm import Target
            tgt = session.get(Target, uid)
            if tgt:
                target_name = tgt.name

        return await self.analyze(
            target=target_name or "unknown",
            records=records,
            task_type=task.type if hasattr(task, "type") else "",
            task_id=task_id,
        )

    def _parse_analysis_result(self, raw_result: dict[str, Any]) -> AISummary:
        """Parse AI analysis output into a structured AISummary."""
        if "error" in raw_result:
            return AISummary(
                summary=f"Analysis error: {raw_result['error']}",
            )

        # Try to parse structured fields
        risk_score = raw_result.get("risk_score", 0.0)
        try:
            risk_score = float(risk_score)
        except (ValueError, TypeError):
            risk_score = 0.0

        risk_score = max(0.0, min(10.0, risk_score))

        return AISummary(
            risk_score=risk_score,
            summary=raw_result.get("summary", ""),
            findings=raw_result.get("findings", []),
            recommendations=raw_result.get("recommendations", []),
            missing_data=raw_result.get("missing_data", []),
        )
