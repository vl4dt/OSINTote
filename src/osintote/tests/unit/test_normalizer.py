# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the target normalizer."""

from __future__ import annotations

import pytest

from osintote.models.orm import RelationshipType
from osintote.workers.normalizer import TargetNormalizer


class TestTargetNormalizer:
    """Tests for TargetNormalizer."""

    @pytest.fixture
    def normalizer(self) -> TargetNormalizer:
        return TargetNormalizer()

    # ── Normalisation ─────────────────────────────────────────────────

    def test_lowercase(self, normalizer: TargetNormalizer) -> None:
        """Target should be lowercased."""
        assert normalizer.normalize("Example.COM") == "example.com"

    def test_strip_trailing_dot(self, normalizer: TargetNormalizer) -> None:
        """Trailing dot should be removed."""
        assert normalizer.normalize("example.com.") == "example.com"

    def test_collapse_consecutive_dots(self, normalizer: TargetNormalizer) -> None:
        """Consecutive dots should be collapsed."""
        assert normalizer.normalize("example..com") == "example.com"

    def test_strip_www(self, normalizer: TargetNormalizer) -> None:
        """www. prefix should be removed."""
        assert normalizer.normalize("www.example.com") == "example.com"

    def test_ipv4_canonical(self, normalizer: TargetNormalizer) -> None:
        """IPv4 should use canonical compressed form."""
        assert normalizer.normalize("010.000.001.001") == "10.0.1.1"
        assert normalizer.normalize("192.168.1.1") == "192.168.1.1"

    def test_ipv6_compressed(self, normalizer: TargetNormalizer) -> None:
        """IPv6 should use compressed form."""
        assert normalizer.normalize("2001:0db8:0000:0000:0000:0000:0000:0001") == "2001:db8::1"

    def test_strips_whitespace(self, normalizer: TargetNormalizer) -> None:
        """Leading/trailing whitespace should be stripped."""
        assert normalizer.normalize("  example.com  ") == "example.com"

    def test_preserves_subdomains(self, normalizer: TargetNormalizer) -> None:
        """Subdomains should be preserved."""
        assert normalizer.normalize("www.sub.example.com") == "sub.example.com"

    def test_www_strips_for_unprotected(self, normalizer: TargetNormalizer) -> None:
        """www should be stripped for unprotected TLDs."""
        assert normalizer.normalize("www.example.com") == "example.com"

    # ── Relationships ─────────────────────────────────────────────────

    def test_link_resolves_to(self, normalizer: TargetNormalizer) -> None:
        """Link with resolves_to type."""
        source, target, rel_type = normalizer.link("example.com", "93.184.216.34", "resolves_to")
        assert source == "example.com"
        assert target == "93.184.216.34"
        assert rel_type == RelationshipType.RESOLVES_TO

    def test_link_invalid_type(self, normalizer: TargetNormalizer) -> None:
        """Invalid relationship type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid relationship type"):
            normalizer.link("example.com", "1.2.3.4", "invalid_type")

    # ── Deduplication ─────────────────────────────────────────────────

    def test_dedup(self, normalizer: TargetNormalizer) -> None:
        """Deduplicate targets preserving order."""
        targets = [
            "example.com.",
            "Example.COM",
            "  www.example.com  ",
            "other.com",
        ]
        result = normalizer.dedup(targets)
        assert result == ["example.com", "other.com"]

    def test_dedup_empty(self, normalizer: TargetNormalizer) -> None:
        """Empty list should return empty."""
        assert normalizer.dedup([]) == []

    def test_dedup_all_same(self, normalizer: TargetNormalizer) -> None:
        """All identical targets should return single entry."""
        result = normalizer.dedup(["example.com", "Example.COM", "example.com."])
        assert result == ["example.com"]

    # ── Relationship resolution ───────────────────────────────────────

    def test_resolve_all(self, normalizer: TargetNormalizer) -> None:
        """Resolve all targets linked to a source."""
        links = [
            ("example.com", "93.184.216.34", RelationshipType.RESOLVES_TO),
            ("example.com", "sub.example.com", RelationshipType.SUBDOMAIN),
            ("other.com", "1.2.3.4", RelationshipType.RESOLVES_TO),
        ]
        results = normalizer.resolve("example.com", links)
        assert results == ["93.184.216.34", "sub.example.com"]

    def test_resolve_by_type(self, normalizer: TargetNormalizer) -> None:
        """Resolve only links of a specific type."""
        links = [
            ("example.com", "93.184.216.34", RelationshipType.RESOLVES_TO),
            ("example.com", "sub.example.com", RelationshipType.SUBDOMAIN),
        ]
        results = normalizer.resolve("example.com", links, target_type="resolves_to")
        assert results == ["93.184.216.34"]

    def test_resolve_no_matches(self, normalizer: TargetNormalizer) -> None:
        """Resolve with no matches should return empty."""
        links = [
            ("other.com", "1.2.3.4", RelationshipType.RESOLVES_TO),
        ]
        results = normalizer.resolve("example.com", links)
        assert results == []
