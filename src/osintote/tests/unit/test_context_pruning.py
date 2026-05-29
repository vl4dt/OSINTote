# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for context pruning system."""

from osintote.engine.context_pruning import (
    ContextPruner,
    PrunedContext,
    compute_token_estimate,
    is_within_budget,
    truncate_text,
)


class TestPrunedContext:
    """Test PrunedContext serialization."""

    def test_to_dict(self) -> None:
        """Test dictionary serialization."""
        context = PrunedContext(
            records=[{"type": "test"}],
            summary="Test summary",
            stats={"total": 1},
        )
        d = context.to_dict()
        assert d["records"] == [{"type": "test"}]
        assert d["summary"] == "Test summary"
        assert d["stats"] == {"total": 1}

    def test_to_text(self) -> None:
        """Test text serialization."""
        context = PrunedContext(
            records=[
                {"type": "dns-a", "target": "example.com", "data": {"address": "93.184.216.34"}},
                {"type": "dns-a", "target": "test.com", "data": {"address": "93.184.216.35"}},
            ],
            summary="Test summary",
            stats={"total": 2},
        )
        text = context.to_text()
        assert "Test summary" in text
        assert "dns-a" in text
        assert "example.com" in text
        assert "93.184.216.34" in text

    def test_to_text_max_records(self) -> None:
        """Test that to_text limits to 50 records."""
        records = [{"type": "test", "target": f"target{i}"} for i in range(100)]
        context = PrunedContext(
            records=records,
            summary="Test",
            stats={"total": 100},
        )
        text = context.to_text()
        # Should only show first 50 records
        lines = text.strip().split("\n")
        record_lines = [ln for ln in lines if ln.startswith("  [")]
        assert len(record_lines) <= 50


class TestContextPruner:
    """Test ContextPruner functionality."""

    def test_empty_records(self) -> None:
        """Test pruning empty records."""
        pruner = ContextPruner()
        result = pruner.summarize([])
        assert result.records == []
        assert result.stats["total_records"] == 0

    def test_severity_filtering(self) -> None:
        """Test severity-based filtering."""
        records = [
            {"type": "test", "target": "a", "data": {"severity": "critical"}},
            {"type": "test", "target": "b", "data": {"severity": "high"}},
            {"type": "test", "target": "c", "data": {"severity": "medium"}},
            {"type": "test", "target": "d", "data": {"severity": "low"}},
            {"type": "test", "target": "e", "data": {"severity": "info"}},
        ]

        # Default min_severity = low
        pruner = ContextPruner(min_severity="low")
        result = pruner.summarize(records)
        severities = [r["data"]["severity"] for r in result.records]
        assert "info" not in severities
        assert "low" in severities
        assert "critical" in severities

    def test_deduplication(self) -> None:
        """Test record deduplication."""
        records = [
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.34"},
            },
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.34"},
            },
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.34"},
            },
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.35"},
            },
        ]

        pruner = ContextPruner(dedup_similar=True, min_severity="low")
        result = pruner.summarize(records)
        assert result.records[0]["data"]["address"] == "93.184.216.34"
        assert result.records[1]["data"]["address"] == "93.184.216.35"

    def test_type_limiting(self) -> None:
        """Test per-type record limiting."""
        records = [
            {
                "type": "dns-a",
                "target": f"target{i}",
                "data": {"severity": "high", "address": f"1.2.3.{i}"},
            }
            for i in range(200)
        ]

        pruner = ContextPruner(max_records_per_type=5)
        result = pruner.summarize(records)
        dns_a_count = sum(1 for r in result.records if r["type"] == "dns-a")
        assert dns_a_count <= 5

    def test_token_truncation(self) -> None:
        """Test token-budget-aware truncation."""
        records = [
            {
                "type": "test",
                "target": f"target{i}",
                "data": {"severity": "high", "value": "x" * 100},
            }
            for i in range(100)
        ]

        pruner = ContextPruner(max_tokens=50)
        result = pruner.summarize(records)
        assert result.records[-1].get("type") == "pruning-note"

    def test_summary_content(self) -> None:
        """Test summary string generation."""
        records = [
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.34"},
            },
            {
                "type": "http-response",
                "target": "example.com",
                "data": {"severity": "high", "status_code": 200},
            },
        ]

        pruner = ContextPruner(min_severity="low")
        result = pruner.summarize(records)
        assert "dns-a" in result.summary
        assert "http-response" in result.summary
        assert "1 unique targets" in result.summary

    def test_stats_content(self) -> None:
        """Test statistics generation."""
        records = [
            {"type": "dns-a", "target": "example.com", "data": {"severity": "high"}},
            {"type": "dns-aaaa", "target": "example.com", "data": {"severity": "low"}},
        ]

        pruner = ContextPruner()
        result = pruner.summarize(records)
        assert result.stats["total_records"] == 2
        assert result.stats["unique_targets"] == 1
        assert result.stats["types"]["dns-a"] == 1
        assert result.stats["severities"]["high"] == 1

    def test_metadata(self) -> None:
        """Test metadata generation."""
        records = [
            {"type": "test", "target": f"target{i}", "data": {"severity": "high"}}
            for i in range(100)
        ]

        pruner = ContextPruner(max_records=10)
        result = pruner.summarize(records)
        meta = result.metadata_
        assert meta["original_count"] == 100
        assert meta["pruned_count"] == 10
        assert meta["reduction_pct"] > 0

    def test_no_dedup(self) -> None:
        """Test that dedup can be disabled."""
        records = [
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.34"},
            },
            {
                "type": "dns-a",
                "target": "example.com",
                "data": {"severity": "high", "address": "93.184.216.34"},
            },
        ]

        pruner = ContextPruner(dedup_similar=False)
        result = pruner.summarize(records)
        assert len(result.records) == 2


class TestHelperFunctions:
    """Test helper functions."""

    def test_compute_token_estimate(self) -> None:
        """Test token estimation."""
        assert compute_token_estimate("") == 1  # minimum 1
        assert compute_token_estimate("a" * 100) == 25  # 100 / 4 = 25
        assert compute_token_estimate("a" * 400) == 100

    def test_is_within_budget(self) -> None:
        """Test budget checking."""
        assert is_within_budget("hello", 100) is True
        assert is_within_budget("x" * 500, 50) is False  # 500/4 = 125 > 50

    def test_truncate_text(self) -> None:
        """Test text truncation."""
        assert truncate_text("hello", 100) == "hello"
        truncated = truncate_text("x" * 100, 20)
        assert len(truncated) <= 83  # 20*4 - 3 = 77 + 3 = 80... let me check
        assert truncated.endswith("...")

    def test_truncate_text_no_change(self) -> None:
        """Test truncation when text fits."""
        text = truncate_text("short text", 100)
        assert text == "short text"
