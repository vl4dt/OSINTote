# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for CLI recon display."""

from osintote.cli.commands.recon import ReconDisplay
from osintote.engine.executor import ExecutionEvent


class TestReconDisplayStageManagement:
    """Test stage tracking in ReconDisplay."""

    def test_add_stage(self) -> None:
        """Test adding a stage for tracking."""
        display = ReconDisplay()
        display.add_stage("dns")
        display.add_stage("http", total=3)
        display.add_stage("whois")

        assert len(display.stages) == 3
        assert display.stages["dns"].name == "dns"
        assert display.stages["dns"].total == 1
        assert display.stages["http"].total == 3
        assert display.stages["whois"].name == "whois"

    def test_update_stage(self) -> None:
        """Test updating a stage's progress."""
        display = ReconDisplay()
        display.add_stage("dns", total=5)
        display.update_stage("dns", completed=3, success=True, elapsed_ms=1500.0)

        assert display.stages["dns"].completed == 3
        assert display.stages["dns"].success is True
        assert display.stages["dns"].elapsed_ms == 1500.0

    def test_complete_stage(self) -> None:
        """Test marking a stage as completed."""
        display = ReconDisplay()
        display.add_stage("dns", total=5)
        display.complete_stage("dns", success=True, elapsed_ms=2000.0)

        assert display.stages["dns"].completed == 5
        assert display.stages["dns"].success is True
        assert display.stages["dns"].elapsed_ms == 2000.0

    def test_fail_stage(self) -> None:
        """Test marking a stage as failed."""
        display = ReconDisplay()
        display.add_stage("dns")
        display.fail_stage("dns", "Connection timeout")

        assert display.stages["dns"].success is False
        assert display.stages["dns"].error == "Connection timeout"


class TestReconDisplayFindingsAndErrors:
    """Test findings and error tracking."""

    def test_add_finding_ok(self) -> None:
        """Test adding an OK finding."""
        display = ReconDisplay()
        display.add_finding(
            {"type": "dns", "target": "example.com", "detail": "1.2.3.4", "status": "ok"}
        )
        assert len(display.findings) == 1
        assert display.findings[0]["type"] == "dns"

    def test_add_finding_warning(self) -> None:
        """Test adding a warning finding."""
        display = ReconDisplay()
        display.add_finding(
            {"type": "http", "target": "test.org", "detail": "404", "status": "warning"}
        )
        assert display.findings[0]["status"] == "warning"

    def test_add_error(self) -> None:
        """Test adding an error entry."""
        display = ReconDisplay()
        display.add_error("dns", "DNS resolution failed")
        assert len(display.errors) == 1
        assert display.errors[0]["stage"] == "dns"
        assert display.errors[0]["message"] == "DNS resolution failed"

    def test_add_log(self) -> None:
        """Test adding log lines."""
        display = ReconDisplay()
        display.add_log("First line")
        display.add_log("Second line")
        assert len(display.log_lines) == 2
        assert "First line" in display.log_lines[0]


class TestReconDisplayEventHandling:
    """Test ExecutionEvent handling."""

    def test_on_event_task_started(self) -> None:
        """Test handling task_started event."""
        display = ReconDisplay()
        event = ExecutionEvent(
            task_id="test-123",
            event_type="task_started",
            data={"target": "example.com", "stages": 3},
        )
        display.on_event(event)
        assert len(display.log_lines) == 2
        assert "example.com" in display.log_lines[0]

    def test_on_event_stage_started(self) -> None:
        """Test handling stage_started event."""
        display = ReconDisplay()
        event = ExecutionEvent(
            task_id="test-123",
            event_type="stage_started",
            stage_name="dns",
        )
        display.on_event(event)
        assert "dns" in display.log_lines[0]

    def test_on_event_stage_complete_success(self) -> None:
        """Test handling successful stage_complete event."""
        display = ReconDisplay()
        display.add_stage("dns", total=1)
        event = ExecutionEvent(
            task_id="test-123",
            event_type="stage_complete",
            stage_name="dns",
            data={"success": True, "message": "Found 5 records", "elapsed_ms": 1200.5},
        )
        display.on_event(event)
        assert display.stages["dns"].success is True
        assert display.stages["dns"].elapsed_ms == 1200.5
        assert len(display.log_lines) == 1
        assert "✓" in display.log_lines[0]

    def test_on_event_stage_complete_failure(self) -> None:
        """Test handling failed stage_complete event."""
        display = ReconDisplay()
        display.add_stage("http", total=1)
        event = ExecutionEvent(
            task_id="test-123",
            event_type="stage_complete",
            stage_name="http",
            data={"success": False, "message": "Connection refused", "elapsed_ms": 500.0},
        )
        display.on_event(event)
        assert display.stages["http"].success is False

    def test_on_event_task_finished(self) -> None:
        """Test handling task_finished event."""
        display = ReconDisplay()
        event = ExecutionEvent(
            task_id="test-123",
            event_type="task_finished",
            data={"status": "completed", "results_count": 15},
        )
        display.on_event(event)
        assert "completed" in display.log_lines[0]
        assert "15" in display.log_lines[1]

    def test_on_event_with_none_data(self) -> None:
        """Test handling events with None data field."""
        display = ReconDisplay()
        event = ExecutionEvent(
            task_id="test-123",
            event_type="task_started",
            data=None,
        )
        display.on_event(event)
        assert len(display.log_lines) == 2  # Should not crash


class TestReconDisplayRendering:
    """Test rendering methods."""

    def test_elapsed_seconds(self) -> None:
        """Test elapsed time property."""
        display = ReconDisplay()
        elapsed = display.elapsed_seconds
        assert elapsed >= 0
        assert elapsed < 1.0  # Should be very small since we just created it

    def test_render_stage_table(self) -> None:
        """Test stage table rendering."""
        display = ReconDisplay()
        display.add_stage("dns", total=5)
        display.update_stage("dns", completed=3, success=True, elapsed_ms=1500.0)

        table = display._render_stage_table()
        assert table is not None
        # Should have 1 row for the stage

    def test_render_findings_table(self) -> None:
        """Test findings table rendering."""
        display = ReconDisplay()
        display.add_finding(
            {"type": "dns", "target": "example.com", "detail": "1.2.3.4", "status": "ok"}
        )
        display.add_finding(
            {"type": "http", "target": "test.org", "detail": "404", "status": "warning"}
        )

        table = display._render_findings_table()
        assert table is not None

    def test_render_findings_table_no_findings(self) -> None:
        """Test findings table with no findings."""
        display = ReconDisplay()
        table = display._render_findings_table()
        assert table is not None  # Returns empty table

    def test_render_errors_panel_no_errors(self) -> None:
        """Test errors panel with no errors."""
        display = ReconDisplay()
        panel = display._render_errors_panel()
        assert panel is None

    def test_render_errors_panel(self) -> None:
        """Test errors panel with errors."""
        display = ReconDisplay()
        display.add_error("dns", "Resolution failed")

        panel = display._render_errors_panel()
        assert panel is not None

    def test_render_log_panel(self) -> None:
        """Test log panel rendering."""
        display = ReconDisplay()
        display.add_log("Line 1")
        display.add_log("Line 2")

        panel = display._render_log_panel()
        assert panel is not None

    def test_render_log_panel_empty(self) -> None:
        """Test log panel with no lines."""
        display = ReconDisplay()
        panel = display._render_log_panel()
        assert panel is not None
        # Should show "(no log output yet)"

    def test_render_summary_no_stages(self) -> None:
        """Test summary with no stages."""
        display = ReconDisplay()
        panel = display._render_summary()
        assert panel is not None

    def test_render(self) -> None:
        """Test full render."""
        display = ReconDisplay()
        display.add_stage("dns", total=3)
        display.update_stage("dns", completed=3, success=True, elapsed_ms=1000.0)

        group = display.render()
        assert group is not None

    def test_render_full(self) -> None:
        """Test full render including log."""
        display = ReconDisplay()
        display.add_stage("dns", total=1)

        group = display.render_full()
        assert group is not None


class TestReconDisplayIntegration:
    """Integration test with StageContext."""

    def test_event_flow_from_context(self) -> None:
        """Test event flow from stage context to display."""
        display = ReconDisplay()
        display.add_stage("test-stage", total=2)

        # Simulate executor event flow
        display.on_event(
            ExecutionEvent(
                task_id="task-1",
                event_type="task_started",
                data={"target": "example.com", "stages": 1},
            )
        )
        display.on_event(
            ExecutionEvent(
                task_id="task-1",
                event_type="stage_started",
                stage_name="test-stage",
            )
        )
        display.on_event(
            ExecutionEvent(
                task_id="task-1",
                event_type="stage_complete",
                stage_name="test-stage",
                data={"success": True, "message": "Done", "elapsed_ms": 500.0},
            )
        )
        display.on_event(
            ExecutionEvent(
                task_id="task-1",
                event_type="task_finished",
                data={"status": "completed", "results_count": 1},
            )
        )

        # Verify state
        assert display.stages["test-stage"].success is True
        assert len(display.log_lines) > 0
