# SPDX-FileCopyrightText: 2026-present Ricardo A. Salgado <ricr.sb@gmail.com>
# SPDX-License-Identifier: MIT
"""Stage strategy pattern — ABC protocol, context, registry, and test helpers.

Every OSINT data source or processing step is a **Stage**: an object that
receives a :class:`StageContext`, executes its work, and returns a
:class:`StageResult`.  Stages are registered in
``STAGE_REGISTRY`` so that recipes and the executor can discover and
invoke them by name.

Example::

    from osintote.engine.stage import Stage, StageContext, StageResult

    class MyStage(Stage):
        name = "my_stage"

        def execute(self, ctx: StageContext) -> StageResult:
            data = fetch_something(ctx.target)
            return StageResult(
                success=True,
                data={"found": True},
                records_count=1,
                message="Found 1 record",
            )
"""

from __future__ import annotations

import abc
import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ..models.orm import TaskStatus

logger = logging.getLogger(__name__)

# ── Result ──────────────────────────────────────────────────────────────────


class StageResult:
    """Outcome of a single stage execution.

    Attributes
    ----------
    success:
        Whether the stage completed without error.
    data:
        Arbitrary payload (dict / list / scalar).
    records_count:
        Number of data records produced.
    message:
        Human-readable summary.
    error:
        Error text, if ``success=False``.
    elapsed_ms:
        Wall-clock time in milliseconds.
    metadata:
        Extra context (cost, retries, warnings).
    """

    __slots__ = (
        "data",
        "elapsed_ms",
        "error",
        "message",
        "metadata",
        "records_count",
        "success",
    )

    def __init__(
        self,
        *,
        success: bool = True,
        data: Any = None,
        records_count: int = 0,
        message: str = "",
        error: str | None = None,
        elapsed_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.data = data
        self.records_count = records_count
        self.message = message
        self.error = error
        self.elapsed_ms = elapsed_ms
        self.metadata = metadata or {}

    @classmethod
    def success_result(
        cls,
        data: Any = None,
        records_count: int = 0,
        message: str = "",
        elapsed_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> StageResult:
        """Helper for happy-path results."""
        return cls(
            success=True,
            data=data,
            records_count=records_count,
            message=message,
            elapsed_ms=elapsed_ms,
            metadata=metadata,
        )

    @classmethod
    def failure(
        cls,
        error: str,
        message: str = "",
        elapsed_ms: float = 0.0,
    ) -> StageResult:
        """Helper for error results."""
        return cls(
            success=False,
            error=error,
            message=message or error,
            elapsed_ms=elapsed_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return {
            "success": self.success,
            "data": self.data,
            "records_count": self.records_count,
            "message": self.message,
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "metadata": self.metadata,
        }


# ── Context ─────────────────────────────────────────────────────────────────


@dataclass
class StageContext:
    """Runtime context shared across all stages in a task.

    This is the single source of truth that stages mutate and query.

    Attributes
    ----------
    target_name:
        Name of the target being investigated.
    target_id:
        Database UUID of the target.
    task_id:
        Database UUID of the task.
    task_status:
        Current lifecycle status (updated by the executor).
    config:
        Engine config snapshot (frozen at task start).
    findings:
        Shared dictionary — stages append their results here.
    records:
        Accumulated records produced by all stages.
    errors:
        Accumulated errors produced by all stages.
    metadata_:
        General-purpose key-value store for cross-stage data.
    """

    target_name: str
    target_id: Any
    task_id: Any
    task_status: str = TaskStatus.PENDING.value
    config: dict[str, Any] = field(default_factory=dict)
    findings: dict[str, Any] = field(default_factory=dict)
    records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata_: dict[str, Any] = field(default_factory=dict, repr=False)

    # Internal (not serialised)
    _start_time: float = field(default_factory=time.time, init=False, repr=False)

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds since context creation."""
        return (time.time() - self._start_time) * 1000

    def copy(self) -> StageContext:
        """Return a shallow copy (findings/records share references)."""
        return copy.copy(self)

    def update_status(self, status: str) -> None:
        """Mutate the current task status."""
        self.task_status = status

    def log_error(self, stage: str, message: str, meta: dict[str, Any] | None = None) -> None:
        """Record an error for later reporting."""
        err: dict[str, Any] = {
            "stage": stage,
            "message": message,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }
        if meta:
            err["meta"] = meta
        self.errors.append(err)


# ── Stage ABC ───────────────────────────────────────────────────────────────


class Stage(abc.ABC):
    """Abstract base class for all OSINT stages.

    Subclasses must define:
    - ``name``: unique identifier (lowercase, e.g. "dns", "http_probe")
    - ``execute()``: core logic returning a ``StageResult``

    Optional overrides:
    - ``cost``: resource cost tier — ``"light"``, ``"medium"``, ``"heavy"``
    - ``retry_on``: set of error sub-string prefixes that trigger retry
    - ``timeout_s``: per-attempt timeout in seconds (0 = unlimited)
    """

    name: str = ""
    cost: str = "medium"  # light | medium | heavy
    retry_on: frozenset[str] = frozenset()  # type: ignore[assignment]
    timeout_s: float = 0.0  # 0 = unlimited

    @abc.abstractmethod
    def execute(self, ctx: StageContext) -> StageResult:
        """Execute the stage's core logic.

        Parameters
        ----------
        ctx:
            The shared execution context.

        Returns
        -------
        StageResult
            The outcome of the execution.
        """

    def _run_with_timeout(
        self,
        ctx: StageContext,
        timeout: float | None = None,
    ) -> StageResult:
        """Run execute() with an optional timeout (threading-based).

        Falls back to no timeout if the platform doesn't support it.
        """
        import threading

        result: StageResult | None = None
        exception: BaseException | None = None

        def _target() -> None:
            nonlocal result, exception
            try:
                result = self.execute(ctx)
            except BaseException as exc:
                exception = exc

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout=timeout or self.timeout_s)

        if t.is_alive():
            return StageResult.failure(
                error=f"Stage '{self.name}' timed out after {timeout or self.timeout_s}s",
                elapsed_ms=ctx.elapsed_ms,
            )
        if exception is not None:
            return StageResult.failure(
                error=str(exception),
                message=f"Stage '{self.name}' failed: {exception}",
                elapsed_ms=ctx.elapsed_ms,
            )
        if result is None:
            return StageResult.failure(
                error="Stage returned None",
                elapsed_ms=ctx.elapsed_ms,
            )
        return result


# ── Registry ────────────────────────────────────────────────────────────────


STAGE_REGISTRY: dict[str, type[Stage]] = {}
"""Map of ``stage_name → Stage subclass``.

Populated automatically via the :func:`register_stage` decorator.
"""


def register_stage(cls: type[Stage] | None = None, name: str | None = None) -> Any:
    """Decorator to register a Stage subclass.

    Usage::

        @register_stage
        class DNSStage(Stage):
            name = "dns"
            ...

        # or explicit name
        @register_stage(name="my_custom")
        class MyCustom(Stage):
            name = "my_custom"
            ...
    """

    def _decorator(cls: type[Stage]) -> type[Stage]:
        stage_name = name or getattr(cls, "name", cls.__name__.lower())
        STAGE_REGISTRY[stage_name] = cls
        logger.debug("Registered stage: %s", stage_name)
        return cls

    if cls is not None:
        return _decorator(cls)
    return _decorator


# ── Test Helpers ────────────────────────────────────────────────────────────


class FakeStage(Stage):
    """A stub stage for unit testing other stages.

    Can be configured to return success or failure results.
    """

    def __init__(
        self,
        *,
        success: bool = True,
        data: Any = None,
        records_count: int = 0,
        message: str = "",
        error: str | None = None,
        raise_on_execute: bool = False,
        execute_delay: float = 0.0,
    ) -> None:
        self._success = success
        self._data = data
        self._records_count = records_count
        self._message = message
        self._error = error
        self._raise = raise_on_execute
        self._delay = execute_delay
        self.call_count = 0

    def execute(self, ctx: StageContext) -> StageResult:
        self.call_count += 1
        if self._delay:
            time.sleep(self._delay)
        if self._raise:
            raise RuntimeError("Fake stage raised intentionally")
        return StageResult(
            success=self._success,
            data=self._data,
            records_count=self._records_count,
            message=self._message,
            error=self._error,
        )


class StageTester:
    """Helper for writing per-stage tests.

    Usage in tests::

        tester = StageTester()
        result = tester.run(DNSStage, ctx)
        assert result.success
        assert result.records_count > 0
    """

    @staticmethod
    def run(
        stage_cls: type[Stage],
        ctx: StageContext,
        *,
        timeout: float | None = None,
        name: str | None = None,
    ) -> StageResult:
        """Instantiate and run a stage, returning the result."""
        instance = stage_cls()
        if name:
            instance.name = name
        runner = instance._run_with_timeout if timeout else instance.execute
        start = time.time()
        result = runner(ctx)
        result.elapsed_ms = (time.time() - start) * 1000
        return result
