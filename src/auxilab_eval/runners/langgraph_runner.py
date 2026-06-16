"""Adapter for LangGraph `Runnable` / compiled graphs.

The import of LangGraph itself is deferred so the harness keeps a clean
dependency profile when the user does not need this runner.
"""

from __future__ import annotations

from typing import Any

from auxilab_eval.runners.base import AgentRunner


class LangGraphRunner(AgentRunner):
    """Wrap a LangGraph runnable / compiled graph.

    Any object exposing `.invoke(payload)` works — that includes LangGraph
    compiled graphs, LangChain Runnables, and most LangChain-style chains.
    Pass the object directly:

        from langgraph.graph import StateGraph
        graph = StateGraph(...).compile()
        runner = LangGraphRunner(graph)
    """

    def __init__(self, graph: Any, *, name: str | None = None) -> None:
        if not hasattr(graph, "invoke"):
            raise TypeError(
                "LangGraphRunner expects an object with an `.invoke(payload)` "
                "method (e.g. a compiled LangGraph or a LangChain Runnable)."
            )
        self._graph = graph
        self.name = name or "langgraph_agent"

    def invoke(self, payload: dict[str, Any]) -> Any:
        return self._graph.invoke(payload)
