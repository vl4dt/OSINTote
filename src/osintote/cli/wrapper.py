# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""CLI wrapper framework — safe async subprocess execution.

Provides a structured subprocess runner using
asyncio.create_subprocess_exec (no shell=True) with:
  - configurable timeouts
  - resource limits (memory/CPU where available)
  - working directory isolation
  - environment isolation
  - structured result capture

Usage::

    runner = SubprocessRunner()
    result = await runner.run("python", "-c", "print('hello')", timeout=30.0)
    print(result.stdout)

On Windows, resource limits (memory/CPU) are not enforced but
timeouts and working dir isolation are still applied.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

# ── Result dataclasses ──────────────────────────────────────────────────────


@dataclass
class SubprocessResult:
    """Result of a subprocess execution."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    killed: bool = False
    pid: int | None = None

    @property
    def success(self) -> bool:
        """Return True if the command exited with code 0."""
        return self.exit_code == 0


@dataclass
class SubprocessError(Exception):
    """Error during subprocess execution."""

    result: SubprocessResult
    message: str


# ── Configuration ───────────────────────────────────────────────────────────


@dataclass
class SubprocessConfig:
    """Configuration for a subprocess execution."""

    timeout: float = 300.0
    max_memory_mb: int | None = None
    max_cpu_percent: int | None = None
    work_dir: Path | None = None
    env: dict[str, str] | None = None
    stdin: str | None = None

    def validate(self) -> None:
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_memory_mb is not None and self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.max_cpu_percent is not None and not 1 <= self.max_cpu_percent <= 400:
            raise ValueError("max_cpu_percent must be between 1 and 400")


# ── Runner ──────────────────────────────────────────────────────────────────


class SubprocessRunner:
    """Safe async subprocess runner.

    Uses asyncio.create_subprocess_exec exclusively — no shell=True,
    no eval, no subprocess.call/run with shell.
    """

    def __init__(self, config: SubprocessConfig | None = None) -> None:
        """Initialise with optional default config."""
        self.config = config or SubprocessConfig()

    async def run(
        self,
        *args: str,
        timeout: float | None = None,
        max_memory_mb: int | None = None,
        max_cpu_percent: int | None = None,
        work_dir: Path | None = None,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> SubprocessResult:
        """Execute a command safely via asyncio.create_subprocess_exec.

        Args:
            *args: Command and arguments (must not include shell=True).
            timeout: Override default timeout in seconds.
            max_memory_mb: Override max memory in MB.
            max_cpu_percent: Override max CPU percentage.
            work_dir: Override working directory.
            env: Override environment variables.
            stdin: Override stdin text.

        Returns:
            SubprocessResult with exit code, output, and timing.

        Raises:
            SubprocessError: If the command fails, times out, or
                exceeds resource limits.
        """
        cfg = SubprocessConfig(
            timeout=timeout or self.config.timeout,
            max_memory_mb=max_memory_mb or self.config.max_memory_mb,
            max_cpu_percent=max_cpu_percent or self.config.max_cpu_percent,
            work_dir=work_dir or self.config.work_dir,
            env=env or self.config.env,
            stdin=stdin or self.config.stdin,
        )
        cfg.validate()

        start = asyncio.get_event_loop().time()
        command = list(args)
        work_dir = cfg.work_dir

        env = cfg.env
        if env is None and work_dir is not None:
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)

        # Start the process
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if cfg.stdin is not None else None,
            cwd=work_dir,
            env=env,
        )

        pid = process.pid

        # Monitor resource limits
        monitor_task: asyncio.Task[None] | None = None
        if cfg.max_memory_mb is not None or cfg.max_cpu_percent is not None:
            monitor_task = asyncio.create_task(self._monitor_resources(pid, process, cfg))

        # Read output with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=cfg.stdin.encode() if cfg.stdin else None),
                timeout=cfg.timeout,
            )
        except TimeoutError:
            process.kill()
            elapsed = (asyncio.get_event_loop().time() - start) * 1000
            if monitor_task:
                monitor_task.cancel()
            result = SubprocessResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=elapsed,
                timed_out=True,
                pid=pid,
            )
            raise SubprocessError(result, "Command timed out") from None

        if monitor_task:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task

        elapsed = (asyncio.get_event_loop().time() - start) * 1000
        result = SubprocessResult(
            command=command,
            exit_code=process.returncode,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            duration_ms=elapsed,
            pid=pid,
        )

        if not result.success:
            raise SubprocessError(
                result,
                f"Command exited with code {process.returncode}",
            )

        return result

    async def _monitor_resources(
        self,
        pid: int,
        process: asyncio.subprocess.Process,
        cfg: SubprocessConfig,
    ) -> None:
        """Monitor resource usage and kill if limits exceeded.

        Uses psutil to check memory and CPU usage of the process tree.
        """
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess, psutil.AccessDenied:
            return

        while True:
            if process.returncode is not None:
                return

            await asyncio.sleep(0.5)

            try:
                mem_info = proc.memory_info()
                mem_mb = mem_info.rss / (1024 * 1024)
                if cfg.max_memory_mb is not None and mem_mb > cfg.max_memory_mb:
                    process.kill()
                    return
            except psutil.NoSuchProcess, psutil.AccessDenied:
                return

            if cfg.max_cpu_percent is not None:
                try:
                    cpu = proc.cpu_percent(interval=0.1)
                    if cpu > cfg.max_cpu_percent:
                        process.kill()
                        return
                except psutil.NoSuchProcess, psutil.AccessDenied:
                    return

    async def run_safe(
        self,
        *args: str,
        timeout: float | None = None,
        max_memory_mb: int | None = None,
        max_cpu_percent: int | None = None,
        work_dir: Path | None = None,
        env: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> SubprocessResult:
        """Execute a command, returning a result even on failure.

        Unlike run(), this catches SubprocessError and returns
        a SubprocessResult with the failure details.

        Args:
            *args: Command and arguments.
            timeout: Override timeout in seconds.
            max_memory_mb: Override max memory in MB.
            max_cpu_percent: Override max CPU percentage.
            work_dir: Override working directory.
            env: Override environment variables.
            stdin: Override stdin text.

        Returns:
            SubprocessResult (may indicate failure via exit_code).
        """
        try:
            return await self.run(
                *args,
                timeout=timeout,
                max_memory_mb=max_memory_mb,
                max_cpu_percent=max_cpu_percent,
                work_dir=work_dir,
                env=env,
                stdin=stdin,
            )
        except SubprocessError as exc:
            return exc.result


# ── CLI command ──────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for the CLI wrapper — used for standalone testing."""
    if len(sys.argv) < 2:
        print("Usage: python -m osintote.cli.wrapper <command> [args...]")
        sys.exit(1)

    async def _run() -> None:
        runner = SubprocessRunner()
        try:
            result = await runner.run(*sys.argv[1:])
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
        except SubprocessError as exc:
            print(f"Error: {exc.message}", file=sys.stderr)
            sys.exit(exc.result.exit_code)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
