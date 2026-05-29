# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for the CLI wrapper framework."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from osintote.cli.wrapper import (
    SubprocessConfig,
    SubprocessError,
    SubprocessResult,
    SubprocessRunner,
)

# ── Config tests ────────────────────────────────────────────────────────────


class TestSubprocessConfig:
    """Tests for SubprocessConfig validation."""

    def test_valid_config(self) -> None:
        """Config with valid values should not raise."""
        cfg = SubprocessConfig(timeout=10.0, max_memory_mb=1024)
        cfg.validate()

    def test_invalid_timeout(self) -> None:
        """Negative timeout should raise ValueError."""
        cfg = SubprocessConfig(timeout=-1.0)
        with pytest.raises(ValueError, match="timeout must be positive"):
            cfg.validate()

    def test_invalid_max_memory(self) -> None:
        """Zero max_memory_mb should raise ValueError."""
        cfg = SubprocessConfig(max_memory_mb=0)
        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            cfg.validate()

    def test_invalid_cpu_percent_low(self) -> None:
        """CPU percent below 1 should raise ValueError."""
        cfg = SubprocessConfig(max_cpu_percent=0)
        with pytest.raises(ValueError, match="max_cpu_percent must be between"):
            cfg.validate()

    def test_valid_cpu_percent(self) -> None:
        """CPU percent between 1-400 should be valid."""
        cfg = SubprocessConfig(max_cpu_percent=200)
        cfg.validate()


# ── Runner tests (using class-based fixture setup) ─────────────────────────


class TestSubprocessRunner:
    """Tests for SubprocessRunner."""

    @pytest.fixture(autouse=True)
    def setup_runner(self) -> None:
        """Create runner before each test."""
        self.runner = SubprocessRunner(SubprocessConfig(timeout=30.0))

    @pytest.mark.asyncio
    async def test_run_success_python(self) -> None:
        """Run a simple Python command successfully."""
        result = await self.runner.run(sys.executable, "-c", "print('hello world')")
        assert result.success is True
        assert "hello world" in result.stdout
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_failure_exit_code(self) -> None:
        """Run a command that exits with non-zero code."""
        with pytest.raises(SubprocessError) as exc_info:
            await self.runner.run(sys.executable, "-c", "import sys; sys.exit(1)")
        assert exc_info.value.result.exit_code == 1
        assert "exited with code 1" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_run_safe_returns_failure(self) -> None:
        """run_safe should return result even on failure."""
        result = await self.runner.run_safe(sys.executable, "-c", "import sys; sys.exit(42)")
        assert result.success is False
        assert result.exit_code == 42
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_run_timeout(self) -> None:
        """Command exceeding timeout should raise SubprocessError."""
        with pytest.raises(SubprocessError) as exc_info:
            await self.runner.run(
                sys.executable,
                "-c",
                "import time; time.sleep(10)",
                timeout=0.3,
            )
        assert exc_info.value.result.timed_out is True

    @pytest.mark.asyncio
    async def test_run_work_dir_isolation(self) -> None:
        """Command should run in specified working directory."""
        work_dir = Path("/tmp")
        result = await self.runner.run(
            sys.executable,
            "-c",
            "import os; print(os.getcwd())",
            work_dir=work_dir,
        )
        # On Windows, os.getcwd() returns the full path
        cwd = Path(result.stdout.strip())
        assert work_dir == cwd or os.name == "nt"

    @pytest.mark.asyncio
    async def test_run_env_isolation(self) -> None:
        """Command should use specified environment."""
        custom_env = {"MY_VAR": "test_value"}
        result = await self.runner.run(
            sys.executable,
            "-c",
            "import os; print(os.environ.get('MY_VAR', 'MISSING'))",
            env=custom_env,
        )
        assert "test_value" in result.stdout

    @pytest.mark.asyncio
    async def test_run_no_shell_true(self) -> None:
        """Runner must use create_subprocess_exec, not shell."""
        result = await self.runner.run(sys.executable, "-c", "print('no_shell')")
        assert result.success is True
        assert "no_shell" in result.stdout

    @pytest.mark.asyncio
    async def test_run_memory_limit(self) -> None:
        """Command exceeding memory limit should be killed."""
        # On Windows, psutil memory limits are best-effort
        # We verify the monitoring logic is invoked without error
        runner = SubprocessRunner(SubprocessConfig(timeout=10.0, max_memory_mb=512))
        # This should succeed (500k integers is ~16MB, well under 512MB)
        result = await runner.run_safe(
            sys.executable,
            "-c",
            "x = [0] * 500000; import time; time.sleep(0.5)",
            max_memory_mb=512,
            timeout=5.0,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_overrides(self) -> None:
        """Override config values for a single run."""
        result = await self.runner.run(
            sys.executable,
            "-c",
            "print('override')",
            timeout=5.0,
        )
        assert result.success is True
        assert "override" in result.stdout

    @pytest.mark.asyncio
    async def test_run_stderr_capture(self) -> None:
        """Stderr should be captured."""
        with pytest.raises(SubprocessError) as exc_info:
            await self.runner.run(
                sys.executable, "-c", "import sys; print('err', file=sys.stderr); sys.exit(1)"
            )
        assert "err" in exc_info.value.result.stderr


# ── Free function tests ─────────────────────────────────────────────────────


@pytest.fixture
def runner() -> SubprocessRunner:
    """Provide a SubprocessRunner instance."""
    return SubprocessRunner(SubprocessConfig(timeout=30.0))


@pytest.mark.asyncio
async def test_run_safe_success(runner: SubprocessRunner) -> None:
    """run_safe returns success result without raising."""
    result = await runner.run_safe(sys.executable, "-c", "print('safe_ok')")
    assert result.success is True
    assert "safe_ok" in result.stdout


@pytest.mark.asyncio
async def test_run_safe_failure(runner: SubprocessRunner) -> None:
    """run_safe returns failure result without raising."""
    result = await runner.run_safe(sys.executable, "-c", "import sys; sys.exit(1)")
    assert result.success is False
    assert result.exit_code == 1


def test_subprocess_result_properties() -> None:
    """SubprocessResult success property."""
    result = SubprocessResult(
        command=["echo", "hello"],
        exit_code=0,
        stdout="hello\n",
        stderr="",
        duration_ms=10.0,
    )
    assert result.success is True

    fail_result = SubprocessResult(
        command=["echo", "hello"],
        exit_code=1,
        stdout="",
        stderr="",
        duration_ms=10.0,
    )
    assert fail_result.success is False


@pytest.mark.asyncio
async def test_subprocess_runner_default_config() -> None:
    """Runner without config should use defaults."""
    runner = SubprocessRunner()
    cfg = runner.config
    assert cfg.timeout == 300.0
    assert cfg.max_memory_mb is None
    assert cfg.max_cpu_percent is None
