# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for AI query engine."""

import pytest

from osintote.ai.query_engine import (
    DSLExecutor,
    DSLParser,
    DSLQuery,
    NLFormatter,
    QueryResult,
)


class TestDSLQuery:
    """Tests for DSLQuery dataclass."""

    def test_defaults(self) -> None:
        q = DSLQuery()
        assert q.table == "records"
        assert q.columns == ["*"]
        assert q.filters == []
        assert q.order_by is None
        assert q.order_dir == "desc"
        assert q.limit == 100


class TestDSLParser:
    """Tests for DSLParser."""

    def test_parse_simple_select_all(self) -> None:
        q = DSLParser.parse("SELECT * FROM records")
        assert q.table == "records"
        assert q.columns == ["*"]

    def test_parse_select_columns(self) -> None:
        q = DSLParser.parse("SELECT severity, message FROM records")
        assert q.columns == ["severity", "message"]

    def test_parse_where_equals(self) -> None:
        q = DSLParser.parse("SELECT * FROM records WHERE severity='critical'")
        assert len(q.filters) == 1
        assert q.filters[0]["column"] == "severity"
        assert q.filters[0]["operator"] == "="
        assert q.filters[0]["value"] == "critical"

    def test_parse_where_not_equals(self) -> None:
        q = DSLParser.parse("SELECT * FROM records WHERE status != 'pending'")
        assert len(q.filters) == 1
        assert q.filters[0]["operator"] == "!="

    def test_parse_order_by_desc(self) -> None:
        q = DSLParser.parse("SELECT * FROM records ORDER BY severity DESC")
        assert q.order_by == "severity"
        assert q.order_dir == "DESC"

    def test_parse_order_by_asc(self) -> None:
        q = DSLParser.parse("SELECT * FROM records ORDER BY name ASC")
        assert q.order_by == "name"
        assert q.order_dir == "ASC"

    def test_parse_limit(self) -> None:
        q = DSLParser.parse("SELECT * FROM records LIMIT 10")
        assert q.limit == 10

    def test_parse_complex(self) -> None:
        q = DSLParser.parse(
            "SELECT severity, message FROM records WHERE severity='critical' ORDER BY severity DESC LIMIT 5"
        )
        assert q.table == "records"
        assert q.columns == ["severity", "message"]
        assert q.filters[0]["value"] == "critical"
        assert q.order_by == "severity"
        assert q.limit == 5

    def test_parse_task_table(self) -> None:
        q = DSLParser.parse("SELECT * FROM tasks WHERE status='running'")
        assert q.table == "tasks"

    def test_parse_target_table(self) -> None:
        q = DSLParser.parse("SELECT name FROM targets")
        assert q.table == "targets"

    def test_parse_invalid_fallback(self) -> None:
        q = DSLParser.parse("random text")
        assert q.table == "records"

    def test_parse_with_semicolon(self) -> None:
        q = DSLParser.parse("SELECT * FROM records;")
        assert q.table == "records"

    def test_parse_multiple_filters_and(self) -> None:
        q = DSLParser.parse("SELECT * FROM records WHERE severity='critical' AND type='vuln'")
        assert len(q.filters) == 2

    def test_parse_with_quotes(self) -> None:
        q = DSLParser.parse("SELECT * FROM records WHERE severity=\"critical\"")
        assert q.filters[0]["value"] == "critical"

    def test_parse_tasks_count(self) -> None:
        q = DSLParser.parse("SELECT count(*) FROM tasks WHERE status='running'")
        assert q.table == "tasks"
        assert q.columns == ["count(*)"]

    def test_parse_invalid_table_fallback(self) -> None:
        q = DSLParser.parse("SELECT * FROM unknown_table")
        assert q.table == "records"  # Falls back to records


class TestDSLExecutor:
    """Tests for DSLExecutor (no DB required)."""

    def test_init(self) -> None:
        def fake_session():
            return None

        executor = DSLExecutor(fake_session)
        assert executor is not None

    def test_execute_empty_result(self) -> None:
        """Executor should return empty results when DB not available."""
        def fake_session():
            from unittest.mock import MagicMock
            return MagicMock()

        executor = DSLExecutor(fake_session)
        dsl = DSLParser.parse("SELECT * FROM records WHERE severity='critical'")
        result = executor.execute(dsl)
        assert isinstance(result, QueryResult)
        assert isinstance(result.count, int)


class TestNLFormatter:
    """Tests for NLFormatter."""

    def test_format_empty_result(self) -> None:
        result = QueryResult(count=0)
        text = NLFormatter.format(result)
        assert "No records" in text

    def test_format_single_result(self) -> None:
        result = QueryResult(
            count=1,
            records=[
                {
                    "severity": "critical",
                    "type": "vuln",
                    "message": "CVE-2025-1234 RCE",
                    "target": "example.com",
                }
            ],
        )
        text = NLFormatter.format(result)
        assert "1 record" in text
        assert "CVE-2025-1234" in text
        assert "example.com" in text

    def test_format_multiple_results(self) -> None:
        result = QueryResult(
            count=3,
            records=[
                {"severity": "critical", "type": "vuln", "message": "RCE"},
                {"severity": "high", "type": "vuln", "message": "SQLi"},
                {"severity": "medium", "type": "port-open", "message": "SSH"},
            ],
        )
        text = NLFormatter.format(result)
        assert "3 record" in text
        assert "RCE" in text
        assert "SQLi" in text

    def test_format_truncation(self) -> None:
        records = [
            {"severity": "info", "type": "info", "message": f"Result {i}"}
            for i in range(25)
        ]
        result = QueryResult(count=25, records=records)
        text = NLFormatter.format(result)
        assert "... and 5 more records" in text

    def test_format_count_only(self) -> None:
        result = QueryResult(count=0)
        text = NLFormatter.format_count(result)
        assert "No matching" in text

    def test_format_count_with_results(self) -> None:
        result = QueryResult(count=42)
        text = NLFormatter.format_count(result)
        assert "Total: 42" in text
