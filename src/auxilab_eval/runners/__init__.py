"""Agent runner adapters.

A runner is a thin shim that turns *anything callable* into a uniform
interface the harness can invoke. Three adapters ship out of the box:

- `PythonRunner`    — wrap a plain Python function or coroutine.
- `LangGraphRunner` — wrap a LangGraph `Runnable` / compiled graph.
- `HttpRunner`      — POST the input payload to an HTTP endpoint.

Implement `AgentRunner` to plug in your own.
"""

from auxilab_eval.runners.base import AgentRunner, RunnerResult
from auxilab_eval.runners.python_runner import PythonRunner
from auxilab_eval.runners.langgraph_runner import LangGraphRunner
from auxilab_eval.runners.http_runner import HttpRunner

__all__ = [
    "AgentRunner",
    "RunnerResult",
    "PythonRunner",
    "LangGraphRunner",
    "HttpRunner",
]
