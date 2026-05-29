# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for AI workflow suggester."""


from osintote.ai.suggester import FindingSuggestion, Suggester


class TestFindingSuggestion:
    """Tests for FindingSuggestion dataclass."""

    def test_create(self) -> None:
        s = FindingSuggestion(
            finding_type="exposed_db",
            severity="critical",
            description="Database exposed",
        )
        assert s.finding_type == "exposed_db"
        assert s.severity == "critical"
        assert s.recommended_actions == []
        assert s.auto_queue is False


class TestSuggester:
    """Tests for the Suggester class."""

    def test_init_without_registry(self) -> None:
        suggester = Suggester()
        assert suggester.registry is None

    def test_detect_critical_no_critical(self) -> None:
        suggester = Suggester()
        records = [
            {"type": "port-open", "data": {"severity": "info", "message": "Port 80 open"}},
        ]
        result = suggester.detect_critical(records)
        assert len(result) == 0

    def test_detect_critical_with_high(self) -> None:
        suggester = Suggester()
        records = [
            {"type": "http-response", "data": {"severity": "high", "message": "phpMyAdmin admin panel detected"}},  # noqa: E501
        ]
        result = suggester.detect_critical(records)
        assert len(result) > 0

    def test_detect_critical_with_critical(self) -> None:
        suggester = Suggester()
        records = [
            {"type": "port-open", "data": {"severity": "critical", "message": "MySQL on port 3306"}},  # noqa: E501
        ]
        result = suggester.detect_critical(records)
        assert len(result) > 0

    def test_has_critical_no(self) -> None:
        records = [
            {"type": "port-open", "data": {"severity": "info"}},
            {"type": "dns-record", "data": {"severity": "low"}},
        ]
        assert Suggester.has_critical_findings(records) is False

    def test_has_critical_yes(self) -> None:
        records = [
            {"type": "vuln", "data": {"severity": "critical"}},
        ]
        assert Suggester.has_critical_findings(records) is True

    def test_generate_exposed_db(self) -> None:
        suggester = Suggester()
        records = [
            {
                "type": "port-open",
                "target": "10.0.0.5",
                "data": {"severity": "high", "message": "MySQL on port 3306"},
            }
        ]
        results = suggester.generate(records, "10.0.0.5")
        db_suggestions = [s for s in results if s.finding_type == "exposed_db"]
        assert len(db_suggestions) == 1
        assert db_suggestions[0].severity == "critical"
        assert len(db_suggestions[0].recommended_actions) > 0
        assert db_suggestions[0].auto_queue is True

    def test_generate_exposed_admin(self) -> None:
        suggester = Suggester()
        records = [
            {
                "type": "http-response",
                "target": "example.com",
                "data": {"severity": "medium", "message": "phpMyAdmin detected"},
            }
        ]
        results = suggester.generate(records, "example.com")
        admin_suggestions = [s for s in results if s.finding_type == "exposed_admin"]
        assert len(admin_suggestions) == 1

    def test_generate_open_ssh(self) -> None:
        suggester = Suggester()
        records = [
            {
                "type": "port-open",
                "target": "example.com",
                "data": {"severity": "medium", "message": "SSH OpenSSH_9.2"},
            }
        ]
        results = suggester.generate(records, "example.com")
        ssh_suggestions = [s for s in results if s.finding_type == "open_ssh"]
        assert len(ssh_suggestions) == 1
        assert ssh_suggestions[0].severity == "medium"

    def test_generate_rdp(self) -> None:
        suggester = Suggester()
        records = [
            {
                "type": "port-open",
                "target": "192.168.1.50",
                "data": {"severity": "high", "message": "RDP on port 3389"},
            }
        ]
        results = suggester.generate(records, "192.168.1.50")
        rdp_suggestions = [s for s in results if s.finding_type == "open_rdp"]
        assert len(rdp_suggestions) == 1

    def test_generate_no_findings(self) -> None:
        suggester = Suggester()
        records = [
            {"type": "port-open", "data": {"severity": "info", "message": "Port 80 open - nginx"}},
        ]
        results = suggester.generate(records, "example.com")
        assert len(results) == 0

    def test_generate_severity_sorting(self) -> None:
        suggester = Suggester()
        records = [
            {
                "type": "port-open",
                "data": {"severity": "medium", "message": "SSH on port 22"},
            },
            {
                "type": "port-open",
                "data": {"severity": "high", "message": "RDP on port 3389"},
            },
            {
                "type": "port-open",
                "data": {"severity": "critical", "message": "MySQL on port 3306"},
            },
        ]
        results = suggester.generate(records, "target")
        severities = [s.severity for s in results]
        expected_order = ["critical", "high", "medium"]
        assert severities == expected_order

    def test_generate_with_ai_suggestions(self) -> None:
        suggester = Suggester()
        records = [
            {
                "type": "port-open",
                "data": {"severity": "critical", "message": "MySQL on port 3306"},
            }
        ]
        results = suggester.generate(records, "target", use_ai=True)
        ai_suggestions = [s for s in results if s.finding_type == "ai_recommendation"]
        assert len(ai_suggestions) == 0  # No registry configured

    def test_generate_empty_records(self) -> None:
        suggester = Suggester()
        results = suggester.generate([], "target")
        assert len(results) == 0

    def test_extract_text_from_record(self) -> None:
        suggester = Suggester()
        record = {
            "type": "port-open",
            "target": "example.com",
            "message": "SSH OpenSSH_9.2",
            "data": {"severity": "medium", "port": 22},
        }
        text = suggester._extract_text(record)
        assert "SSH" in text
        assert "OpenSSH" in text
        assert "example.com" in text
