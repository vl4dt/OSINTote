# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""End-to-end integration test — full OSINT pipeline flow.

Tests the complete workflow:
  target → DNS → HTTP → results → report

This test simulates a real recon session using FakeStage instances
and verifies all integration points: database, executor, WAL, API,
and report generation.

Example::

    pytest src/osintote/tests/integration/test_end_to_end.py -v
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine as sync_create_engine
from sqlalchemy.orm import Session, sessionmaker

from osintote.engine.executor import Executor
from osintote.engine.stage import FakeStage
from osintote.engine.wal import WriteAheadLog
from osintote.models.orm import RecordType, TaskStatus
from osintote.notify.notifier import Notifier
from osintote.reports import Reporter, ReportFormat

# ── Dummy notifier for tests ─────────────────────────────────────────────────


class NoOpNotifier(Notifier):
    """A no-op notifier for test isolation."""

    async def on_task_complete(
        self,
        task_id: str,
        target_name: str,
        extra: dict | None = None,
    ) -> None:
        pass

    async def on_task_fail(
        self,
        task_id: str,
        target_name: str,
        error_message: str | None = None,
    ) -> None:
        pass


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def db_session() -> Session:
    """Provide a transactional in-memory database session that rolls back."""
    sync_engine = sync_create_engine("sqlite+pysqlite:///:memory:")
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(sync_engine)
    sessionlocal = sessionmaker(sync_engine)
    session = sessionlocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ── Full Pipeline Test ───────────────────────────────────────────────────────


def test_full_pipeline(db_session: Session) -> None:
    """End-to-end: target → DNS → HTTP → results → WAL verification.

    1. Create a target in the database
    2. Create a task linked to the target
    3. Execute the task with fake DNS and HTTP stages via the Executor
    4. Verify task status transitions (pending → running → completed)
    5. Verify records were produced
    6. Verify WAL persistence
    """
    # Step 1: Create target
    from osintote.models.orm import Target

    db_session.add(Target(name="example.com", type="domain", description="E2E test target"))
    db_session.commit()

    # Step 2: Create task
    from osintote.models.orm import Task as TaskModel

    task = TaskModel(name="e2e-recon", status=TaskStatus.PENDING, recipe="quick-scan")
    db_session.add(task)
    db_session.commit()
    task_id = str(task.id)

    # Step 3: Execute with fake stages
    tmp_path = Path("/tmp/e2e_wal")
    tmp_path.mkdir(parents=True, exist_ok=True)
    wal_path = str(tmp_path / "wal.jsonl")
    wal = WriteAheadLog(wal_path=wal_path, checkpoint_s=10.0)

    dns_stage = FakeStage(
        success=True,
        records_count=1,
        message="DNS lookup complete",
        data=[
            {
                "id": str(uuid.uuid4()),
                "type": RecordType.DNS.value,
                "target": "example.com",
                "data": {"addresses": ["93.184.216.34"], "hostnames": ["example.com"]},
            }
        ],
    )

    http_stage = FakeStage(
        success=True,
        records_count=1,
        message="HTTP probe complete",
        data=[
            {
                "id": str(uuid.uuid4()),
                "type": RecordType.HTTP.value,
                "target": "example.com",
                "data": {"status_code": 200, "server": "nginx", "content_type": "text/html"},
            }
        ],
    )

    executor = Executor(max_concurrent=1, notifier=NoOpNotifier(), wal=wal)

    # Run executor synchronously via asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(wal.start())
        loop.run_until_complete(executor.start())
        loop.run_until_complete(
            executor.submit(task_id, "example.com", [dns_stage, http_stage], priority=1)
        )
        loop.run_until_complete(asyncio.sleep(0.5))
        loop.run_until_complete(executor.stop())
        loop.run_until_complete(wal.stop())
    finally:
        loop.close()

    # Step 4: Verify task results
    results = executor.get_task_results(task_id)
    assert results is not None
    assert len(results) == 2
    for result in results:
        assert result.success is True

    # Step 5: Verify records produced
    dns_count = sum(
        1
        for r in results
        if r.data
        and isinstance(r.data, list)
        and any(rec.get("type") == RecordType.DNS.value for rec in r.data)
    )
    http_count = sum(
        1
        for r in results
        if r.data
        and isinstance(r.data, list)
        and any(rec.get("type") == RecordType.HTTP.value for rec in r.data)
    )
    assert dns_count > 0, "DNS records should be produced"
    assert http_count > 0, "HTTP records should be produced"

    # Step 6: Verify WAL persistence
    assert Path(wal_path).exists()
    with open(wal_path) as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) > 0, "WAL should contain task entries"

    entries = [json.loads(line) for line in lines]
    statuses = [
        e["data"]["status"] for e in entries if e["entity"] == "task" and "status" in e["data"]
    ]
    assert "running" in statuses, "WAL should contain RUNNING status"
    assert "completed" in statuses, "WAL should contain COMPLETED status"


# ── Integration test: API structure ────────────────────────────────────────


def test_api_routes_registered() -> None:
    """Test that API routes are properly registered."""
    from osintote.api.app import app

    paths = [route.path for route in app.routes]
    assert "/api/health" in paths
    assert "/api/tasks" in paths
    assert "/api/errors/stream" in paths
    assert "/api/logs/stream" in paths
    assert "/api/docs" in paths


# ── Integration test: Report generation ──────────────────────────────────────


def test_report_generation(tmp_path: Path) -> None:
    """Test report generation from task data.

    Verifies the Reporter service produces valid JSON, Markdown, and HTML reports.
    """
    task_id = uuid.uuid4()
    output_dir = tmp_path / "reports"

    reporter = Reporter(task_id=task_id, output_dir=output_dir)

    mock_data = {
        "task": {
            "id": str(task_id),
            "name": "e2e-test-task",
            "status": "completed",
            "created_at": "2026-01-01T00:00:00Z",
            "completed_at": "2026-01-01T00:01:00Z",
            "recipe": "quick-scan",
        },
        "records": [
            {
                "id": str(uuid.uuid4()),
                "type": "dns",
                "target": "example.com",
                "data": {"addresses": ["93.184.216.34"]},
                "created_at": "2026-01-01T00:00:30Z",
            },
            {
                "id": str(uuid.uuid4()),
                "type": "http",
                "target": "example.com",
                "data": {"status_code": 200},
                "created_at": "2026-01-01T00:00:45Z",
            },
        ],
        "metadata": {
            "total_records": 2,
            "record_types": ["dns", "http"],
        },
    }

    # Replace the method with a lambda to avoid database access
    reporter._collect_task_data = lambda: mock_data  # type: ignore[assignment]

    # Generate JSON report
    json_path = reporter.export(ReportFormat.JSON, filename="e2e-test.json")
    assert json_path.exists()
    content = json.loads(json_path.read_text(encoding="utf-8"))
    assert content["task"]["name"] == "e2e-test-task"
    assert len(content["records"]) == 2

    # Generate Markdown report
    md_path = reporter.export(ReportFormat.MARKDOWN, filename="e2e-test.md")
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert "e2e-test-task" in md_content
    assert "example.com" in md_content

    # Generate HTML report
    html_path = reporter.export(ReportFormat.HTML, filename="e2e-test.html")
    assert html_path.exists()
    html_content = html_path.read_text(encoding="utf-8")
    assert "e2e-test-task" in html_content
    assert "example.com" in html_content
    assert "visNetwork" in html_content or "vis.js" in html_content

    # Verify all files exist
    assert output_dir.exists()
    files = list(output_dir.iterdir())
    assert len(files) == 3

    # Generate all formats at once
    all_reports = reporter.generate_all(filename_prefix="all")
    assert len(all_reports) == 3
    for fmt, path in all_reports.items():
        assert path.exists(), f"{fmt} report at {path} should exist"
