# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the Stage strategy pattern."""

from __future__ import annotations

import threading
import time

import pytest

from osintote.engine.stage import (
    FakeStage,
    Stage,
    StageContext,
    StageResult,
    StageTester,
    register_stage,
    STAGE_REGISTRY,
    TaskStatus,
)


# ── StageResult ──────────────────────────────────────────────────────────────


class TestStageResult:
    """Tests for StageResult class."""

    def test_success_result_default(self) -> None:
        result = StageResult()
        assert result.success is True
        assert result.data is None
        assert result.records_count == 0
        assert result.message == ""
        assert result.error is None
        assert result.elapsed_ms == 0.0
        assert result.metadata == {}

    def test_success_result_full(self) -> None:
        result = StageResult(
            success=True,
            data={"found": True},
            records_count=5,
            message="Found 5 records",
            elapsed_ms=123.45,
            metadata={"retries": 0},
        )
        assert result.to_dict() == {
            "success": True,
            "data": {"found": True},
            "records_count": 5,
            "message": "Found 5 records",
            "error": None,
            "elapsed_ms": 123.45,
            "metadata": {"retries": 0},
        }

    def test_success_result_helper(self) -> None:
        result = StageResult.success_result(
            data={"ip": "1.2.3.4"},
            records_count=1,
            message="Found 1 IP",
            elapsed_ms=50.0,
        )
        assert result.success is True
        assert result.data == {"ip": "1.2.3.4"}

    def test_failure_result(self) -> None:
        result = StageResult.failure(error="Connection refused")
        assert result.success is False
        assert result.error == "Connection refused"
        assert result.message == "Connection refused"

    def test_failure_result_custom_message(self) -> None:
        result = StageResult.failure(error="Timeout", message="DNS lookup timed out")
        assert result.error == "Timeout"
        assert result.message == "DNS lookup timed out"

    def test_elapsed_ms_rounding(self) -> None:
        result = StageResult(elapsed_ms=123.456789)
        assert result.to_dict()["elapsed_ms"] == 123.46

    def test_metadata_default_empty_dict(self) -> None:
        result = StageResult()
        assert isinstance(result.metadata, dict)
        result.metadata["key"] = "value"
        assert result.metadata["key"] == "value"


# ── StageContext ────────────────────────────────────────────────────────────


class TestStageContext:
    """Tests for StageContext dataclass."""

    def test_creation_defaults(self) -> None:
        ctx = StageContext(
            target_name="example.com",
            target_id="test-target-id",
            task_id="test-task-id",
        )
        assert ctx.target_name == "example.com"
        assert ctx.target_id == "test-target-id"
        assert ctx.task_id == "test-task-id"
        assert ctx.task_status == TaskStatus.PENDING.value
        assert ctx.config == {}
        assert ctx.findings == {}
        assert ctx.records == []
        assert ctx.errors == []
        assert ctx.metadata_ == {}
        assert ctx.elapsed_ms >= 0

    def test_elapsed_ms_increases(self) -> None:
        ctx = StageContext(
            target_name="test.com",
            target_id="tid",
            task_id="tid2",
        )
        time.sleep(0.05)
        assert ctx.elapsed_ms > 50  # at least 50ms

    def test_copy(self) -> None:
        ctx = StageContext(
            target_name="test.com",
            target_id="tid",
            task_id="tid2",
        )
        ctx.findings["key"] = "value"
        ctx2 = ctx.copy()
        assert ctx2.target_name == ctx.target_name
        assert ctx2.findings == ctx.findings
        # Shallow copy — modifications to findings affect both
        ctx2.findings["new"] = "data"
        assert ctx.findings["new"] == "data"

    def test_update_status(self) -> None:
        ctx = StageContext(
            target_name="test.com",
            target_id="tid",
            task_id="tid2",
        )
        ctx.update_status(TaskStatus.RUNNING.value)
        assert ctx.task_status == TaskStatus.RUNNING.value
        ctx.update_status(TaskStatus.COMPLETED.value)
        assert ctx.task_status == TaskStatus.COMPLETED.value

    def test_log_error(self) -> None:
        ctx = StageContext(
            target_name="test.com",
            target_id="tid",
            task_id="tid2",
        )
        ctx.log_error("dns", "DNS lookup failed", {"query": "example.com"})
        assert len(ctx.errors) == 1
        assert ctx.errors[0]["stage"] == "dns"
        assert ctx.errors[0]["message"] == "DNS lookup failed"
        assert ctx.errors[0]["meta"]["query"] == "example.com"

    def test_log_error_no_meta(self) -> None:
        ctx = StageContext(
            target_name="test.com",
            target_id="tid",
            task_id="tid2",
        )
        ctx.log_error("http", "HTTP probe failed")
        assert len(ctx.errors) == 1
        assert "meta" not in ctx.errors[0]


# ── Stage ABC ────────────────────────────────────────────────────────────────


class ConcreteStage(Stage):
    """A concrete implementation for testing."""

    name = "concrete"
    cost = "light"

    def __init__(self, *, return_success: bool = True, data: Any = None, delay: float = 0.0) -> None:
        self._success = return_success
        self._data = data
        self._delay = delay
        self.call_count = 0

    def execute(self, ctx: StageContext) -> StageResult:
        self.call_count += 1
        if self._delay:
            time.sleep(self._delay)
        return StageResult.success_result(
            data=self._data,
            message=f"Stage '{self.name}' ran {self.call_count} times",
        )


class FailingStage(Stage):
    name = "failing"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult.failure(error="Intentional failure")


class RaisingStage(Stage):
    name = "raising"

    def execute(self, ctx: StageContext) -> StageResult:
        raise RuntimeError("BANG")


class TestStage:
    """Tests for Stage ABC."""

    def test_abstract_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            Stage()  # type: ignore[abstract]

    def test_concrete_execution(self) -> None:
        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        stage = ConcreteStage(data={"ip": "1.2.3.4"})
        result = stage.execute(ctx)
        assert result.success is True
        assert result.data == {"ip": "1.2.3.4"}
        assert stage.call_count == 1

    def test_stage_default_attrs(self) -> None:
        stage = ConcreteStage()
        assert stage.name == "concrete"
        assert stage.cost == "light"
        assert isinstance(stage.retry_on, frozenset)

    def test_failing_stage(self) -> None:
        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        stage = FailingStage()
        result = stage.execute(ctx)
        assert result.success is False
        assert result.error == "Intentional failure"

    def test_raising_stage_returns_failure(self) -> None:
        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        stage = RaisingStage()
        result = stage._run_with_timeout(ctx)
        assert result.success is False
        assert "BANG" in result.error

    def test_timeout_returns_failure(self) -> None:
        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        slow_stage = ConcreteStage(delay=5.0)
        result = slow_stage._run_with_timeout(ctx, timeout=0.05)
        assert result.success is False
        assert "timed out" in result.error

    def test_execute_returns_none_raises(self) -> None:
        """If a stage returns None, _run_with_timeout should report failure."""

        class NoneStage(Stage):
            name = "none"

            def execute(self, ctx: StageContext) -> None:  # type: ignore[return]
                pass

        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        stage = NoneStage()
        result = stage._run_with_timeout(ctx)
        assert result.success is False
        assert "returned None" in result.error


# ── register_stage decorator ────────────────────────────────────────────────


class TestRegisterStage:
    """Tests for the register_stage decorator."""

    def test_decorator_registers(self) -> None:
        initial = len(STAGE_REGISTRY)

        @register_stage
        class TestRegStage(Stage):
            name = "test_reg"

            def execute(self, ctx: StageContext) -> StageResult:
                return StageResult.success_result()

        assert len(STAGE_REGISTRY) == initial + 1
        assert "test_reg" in STAGE_REGISTRY
        assert STAGE_REGISTRY["test_reg"] is TestRegStage

    def test_decorator_explicit_name(self) -> None:
        @register_stage(name="custom_name")
        class CustomStage(Stage):
            name = "different_name"

            def execute(self, ctx: StageContext) -> StageResult:
                return StageResult.success_result()

        assert "custom_name" in STAGE_REGISTRY
        assert STAGE_REGISTRY["custom_name"] is CustomStage

    def test_decorator_no_parentheses(self) -> None:
        @register_stage
        class AutoNameStage(Stage):
            name = "auto_name_stage"

            def execute(self, ctx: StageContext) -> StageResult:
                return StageResult.success_result()

        assert "auto_name_stage" in STAGE_REGISTRY


# ── FakeStage ───────────────────────────────────────────────────────────────


class TestFakeStage:
    """Tests for FakeStage test helper."""

    def test_successful_fake(self) -> None:
        stage = FakeStage(success=True, data={"found": True}, records_count=3, message="OK")
        result = stage.execute(
            StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        )
        assert result.success is True
        assert result.data == {"found": True}
        assert result.records_count == 3

    def test_failing_fake(self) -> None:
        stage = FakeStage(success=False, error="Simulated failure")
        result = stage.execute(
            StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        )
        assert result.success is False
        assert result.error == "Simulated failure"

    def test_raises_fake(self) -> None:
        stage = FakeStage(raise_on_execute=True)
        result = stage._run_with_timeout(
            StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        )
        assert result.success is False
        assert "intentionally" in result.error

    def test_delay_fake(self) -> None:
        stage = FakeStage(execute_delay=0.05)
        start = time.time()
        result = stage.execute(
            StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        )
        elapsed = time.time() - start
        assert elapsed >= 0.04  # at least the delay
        assert result.success is True

    def test_call_count(self) -> None:
        stage = FakeStage()
        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        stage.execute(ctx)
        stage.execute(ctx)
        stage.execute(ctx)
        assert stage.call_count == 3


# ── StageTester ─────────────────────────────────────────────────────────────


class TestStageTester:
    """Tests for StageTester."""

    def test_run_successful_stage(self) -> None:
        result = StageTester.run(
            ConcreteStage,
            StageContext(target_name="test.com", target_id="tid", task_id="tid2"),
        )
        assert result.success is True

    def test_run_with_timeout(self) -> None:
        result = StageTester.run(
            ConcreteStage,
            StageContext(target_name="test.com", target_id="tid", task_id="tid2"),
            timeout=5.0,
        )
        assert result.success is True

    def test_run_with_custom_name(self) -> None:
        result = StageTester.run(
            ConcreteStage,
            StageContext(target_name="test.com", target_id="tid", task_id="tid2"),
            name="custom_name",
        )
        assert result.success is True


# ── Integration: Stage + Context ───────────────────────────────────────────


class TestStageIntegration:
    """Integration tests for Stage + Context interaction."""

    def test_stage_mutation_of_context(self) -> None:
        class MutatingStage(Stage):
            name = "mutating"

            def execute(self, ctx: StageContext) -> StageResult:
                ctx.findings["from_stage"] = True
                ctx.records.append({"type": "dns", "data": "A record"})
                ctx.log_error("mutating", "Minor issue", {"detail": "x"})
                return StageResult.success_result(message="Mutated ctx")

        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        result = MutatingStage().execute(ctx)
        assert result.success is True
        assert ctx.findings["from_stage"] is True
        assert len(ctx.records) == 1
        assert len(ctx.errors) == 1
        assert ctx.errors[0]["stage"] == "mutating"

    def test_multiple_stages_share_context(self) -> None:
        class StageA(Stage):
            name = "stage_a"

            def execute(self, ctx: StageContext) -> StageResult:
                ctx.findings["a"] = "done"
                return StageResult.success_result()

        class StageB(Stage):
            name = "stage_b"

            def execute(self, ctx: StageContext) -> StageResult:
                # Reads what StageA wrote
                assert ctx.findings.get("a") == "done"
                ctx.findings["b"] = "done"
                return StageResult.success_result()

        ctx = StageContext(target_name="test.com", target_id="tid", task_id="tid2")
        StageA().execute(ctx)
        result_b = StageB().execute(ctx)
        assert result_b.success is True
        assert ctx.findings["b"] == "done"
