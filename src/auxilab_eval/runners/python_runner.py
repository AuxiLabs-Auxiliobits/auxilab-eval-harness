"""Run a plain Python callable (sync or async) as an agent."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable

from auxilab_eval.runners.base import AgentRunner


class PythonRunner(AgentRunner):
    """Wraps a Python function so it can be evaluated by the harness.

    The callable receives the test case `input` payload (a dict) as its only
    argument and must return any JSON-serialisable structure. Coroutines are
    awaited automatically.
    """

    def __init__(
        self,
        fn: Callable[[dict[str, Any]], Any],
        *,
        name: str | None = None,
    ) -> None:
        if not callable(fn):
            raise TypeError("PythonRunner requires a callable.")
        self._fn = fn
        self.name = name or getattr(fn, "__name__", "python_agent")

    def invoke(self, payload: dict[str, Any]) -> Any:
        result = self._fn(payload)
        if inspect.iscoroutine(result):
            return asyncio.run(_drive(result))
        return result


async def _drive(coro):  # pragma: no cover - trivial
    return await coro
