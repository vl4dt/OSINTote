# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for AI analysis engine."""

import pytest

from osintote.ai.analysis_engine import (
    AnalysisEngine,
    AnalysisResult,
    PromptBuilder,
)
from osintote.ai.models import AISummary
from osintote.ai.provider import AIProviderRegistry


class TestAnalysisResult:
    """Tests for AnalysisResult."""

    def test_to_dict(self) -> None:
        summary = AISummary(
            risk_score=7.5,
            summary="Test summary",
            findings=[{"severity": "high", "category": "test", "evidence": "e", "recommendation": "r"}],
        )
        result = AnalysisResult(
            summary=summary,
            model_used="llama3",
            task_id="task-1",
            created_at="2026-05-28T00:00:00+00:00",
        )
        d = result.to_dict()
        assert d["model_used"] == "llama3"
        assert d["task_id"] == "task-1"
        assert d["summary"]["risk_score"] == 7.5
        assert len(d["summary"]["findings"]) == 1


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    def test_build_basic(self) -> None:
        user, system = PromptBuilder.build(
            target="example.com",
            pruned_context={
                "records": [
                    {"type": "port-open", "data": {"severity": "critical", "message": "MySQL on 3306"}},
                    {"type": "port-open", "data": {"severity": "info", "message": "HTTP on 80"}},
                ],
                "stats": {"total_records": 2, "unique_targets": 1, "types": {}, "severities": {}},
                "summary": "2 records found",
            },
            task_type="recon",
        )
        assert "example.com" in user
        assert "3306" in user
        assert "MySQL" in user
        assert "recon" in user
        assert "risk_score" in system

    def test_build_empty_records(self) -> None:
        user, _ = PromptBuilder.build(
            target="empty.com",
            pruned_context={
                "records": [],
                "stats": {"total_records": 0, "unique_targets": 0},
                "summary": "No records",
            },
        )
        assert "empty.com" in user
        assert "Total records: 0" in user

    def test_build_no_task_type(self) -> None:
        user, _ = PromptBuilder.build(
            target="test.com",
            pruned_context={
                "records": [],
                "stats": {},
                "summary": "",
            },
            task_type="",
        )
        assert "Task type: recon" in user

    def test_system_prompt_includes_json_structure(self) -> None:
        _, system = PromptBuilder.build(
            target="test.com",
            pruned_context={"records": [], "stats": {}, "summary": ""},
        )
        assert "risk_score" in system
        assert "summary" in system
        assert "findings" in system
        assert "severity" in system
        assert "evidence" in system
        assert "recommendation" in system
        assert "missing_data" in system


class TestAnalysisEngine:
    """Tests for AnalysisEngine."""

    @pytest.mark.asyncio
    async def test_disabled_analyze(self) -> None:
        """Analysis should return error when registry is disabled."""
        from osintote.engine.config import AIClientConfig

        config = AIClientConfig(enabled=False)
        registry = AIProviderRegistry(config)
        engine = AnalysisEngine(registry)

        result = await engine.analyze(
            target="example.com",
            records=[
                {"type": "vuln", "data": {"severity": "critical", "message": "RCE"}}
            ],
        )
        assert "disabled" in result.summary.summary.lower()

    def test_parse_error_result(self) -> None:
        engine = AnalysisEngine(AIProviderRegistry())
        result = engine._parse_analysis_result({"error": "connection failed"})
        assert "connection failed" in result.summary
        assert result.risk_score == 0.0

    def test_parse_valid_result(self) -> None:
        engine = AnalysisEngine(AIProviderRegistry())
        result = engine._parse_analysis_result({
            "risk_score": 8.0,
            "summary": "High risk detected",
            "findings": [
                {
                    "severity": "critical",
                    "category": "vuln",
                    "evidence": "CVE-2025-1234",
                    "recommendation": "Patch immediately",
                }
            ],
            "recommendations": ["Patch all systems"],
            "missing_data": ["No network scan available"],
        })
        assert result.risk_score == 8.0
        assert result.summary == "High risk detected"
        assert len(result.findings) == 1
        assert result.findings[0]["severity"] == "critical"
        assert result.recommendations == ["Patch all systems"]
        assert result.missing_data == ["No network scan available"]

    def test_parse_result_clamps_score(self) -> None:
        engine = AnalysisEngine(AIProviderRegistry())
        result = engine._parse_analysis_result({"risk_score": 15.0})
        assert result.risk_score == 10.0

    def test_parse_result_negative_clamps(self) -> None:
        engine = AnalysisEngine(AIProviderRegistry())
        result = engine._parse_analysis_result({"risk_score": -5.0})
        assert result.risk_score == 0.0

    def test_parse_result_invalid_score(self) -> None:
        engine = AnalysisEngine(AIProviderRegistry())
        result = engine._parse_analysis_result({"risk_score": "not a number"})
        assert result.risk_score == 0.0
