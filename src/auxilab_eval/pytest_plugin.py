"""pytest plugin for auxilab-eval.

Exposes:

- The `eval_harness` fixture — a thin builder around `EvalHarness`.
- A `--auxilab-eval` CLI flag that, combined with the fixture, lets teams
  drop YAML eval suites straight into their CI test runs.

Usage in a project's conftest.py:

    pytest_plugins = ["auxilab_eval.pytest_plugin"]

Usage in a test:

    def test_my_agent(eval_harness):
        report = eval_harness.run_against(my_agent_fn, "tests.yaml")
        assert report.pass_rate >= 0.8
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Union

import pytest

from auxilab_eval.harness import EvalHarness, EvalReport
from auxilab_eval.runners import AgentRunner, PythonRunner


def pytest_addoption(parser):  # pragma: no cover - pytest hook
    group = parser.getgroup("auxilab-eval")
    group.addoption(
        "--auxilab-eval-html",
        action="store",
        default=None,
        metavar="PATH",
        help="Write an HTML eval report to PATH (used by the eval_harness fixture).",
    )
    group.addoption(
        "--auxilab-eval-no-llm",
        action="store_true",
        default=False,
        help="Disable the LLM-based failure analyser during this test run.",
    )


class _PytestEvalHarness:
    """Thin builder: lets a test function point at a YAML file + an agent."""

    def __init__(self, request: pytest.FixtureRequest) -> None:
        self._request = request

    # ---- public helpers --------------------------------------------------

    def run_against(
        self,
        agent: Union[AgentRunner, Callable[[dict[str, Any]], Any]],
        test_cases: Union[str, Path, list[Any]],
        *,
        history_db: Optional[Union[str, Path]] = None,
    ) -> EvalReport:
        """Run an evaluation and return the report (no assertion)."""
        runner = agent if isinstance(agent, AgentRunner) else PythonRunner(agent)
        analyse = not self._request.config.getoption("--auxilab-eval-no-llm")
        harness = EvalHarness(
            runner=runner,
            test_cases=test_cases,
            analyse_failures=analyse,
            history_db=history_db,
        )
        report = harness.run()
        self._maybe_emit_html(report)
        return report

    def assert_passes(
        self,
        test_cases: Union[str, Path, list[Any]],
        *,
        agent: Union[AgentRunner, Callable[[dict[str, Any]], Any]],
        min_pass_rate: float = 1.0,
        history_db: Optional[Union[str, Path]] = None,
    ) -> EvalReport:
        """Run and assert the pass rate meets `min_pass_rate`."""
        report = self.run_against(agent, test_cases, history_db=history_db)
        if report.pass_rate < min_pass_rate:
            failures = "\n".join(
                f"  - {r.test_case.id}: "
                f"{(r.failure_report.summary if r.failure_report else 'failed')}"
                for r in report.results if not r.passed
            )
            raise AssertionError(
                f"Eval pass rate {report.pass_rate:.0%} < required {min_pass_rate:.0%}.\n"
                + (failures or "")
            )
        return report

    # ---- internals -------------------------------------------------------

    def _maybe_emit_html(self, report: EvalReport) -> None:
        path = self._request.config.getoption("--auxilab-eval-html")
        if path:
            report.to_html(path)


@pytest.fixture
def eval_harness(request) -> _PytestEvalHarness:
    """Pytest fixture exposing a builder for eval runs."""
    return _PytestEvalHarness(request)
