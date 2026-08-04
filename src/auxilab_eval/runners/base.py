"""Abstract base class for agent runners."""

from __future__ import annotations

import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RunnerResult:
    """Captured outcome of a single agent invocation."""

    output: Any
    duration_ms: float
    error: Optional[str] = None
    traceback: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None


class AgentRunner(ABC):
    """Base interface every runner must implement.

    Implementations must be **side-effect free** in `__init__`: heavy resources
    (model clients, network sessions) should be initialised lazily so test
    discovery is fast.
    """

    name: str = "agent"

    @abstractmethod
    def invoke(self, payload: dict[str, Any]) -> Any:
        """Run the underlying agent against `payload` and return the output.

        Implementations should return a JSON-serialisable structure when
        possible (dict / list / str / number) so evaluators can introspect it.
        """

    def run(self, payload: dict[str, Any]) -> RunnerResult:
        """Invoke the agent with timing + structured error capture.

        This is what the harness calls. Subclasses should override `invoke`,
        not `run`, so they get error capture for free.
        """
        start = time.perf_counter()
        try:
            output = self.invoke(payload)
            duration = (time.perf_counter() - start) * 1000.0
            return RunnerResult(output=output, duration_ms=duration)
        except Exception as exc:  # noqa: BLE001 - we want to capture *any* failure
            duration = (time.perf_counter() - start) * 1000.0
            return RunnerResult(
                output=None,
                duration_ms=duration,
                error=f"{type(exc).__name__}: {exc}",
                traceback=traceback.format_exc(),
            )
