"""The `EvalHarness` — orchestrates runner, evaluators, failure analyser, report.

Typical use:

    harness = EvalHarness(
        runner=PythonRunner(my_agent),
        test_cases="tests.yaml",
    )
    report = harness.run()
    report.to_html("report.html")
    print(report.summary())
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from auxilab_eval.evaluators.base import EvaluationResult, get_evaluator
from auxilab_eval.failure_analyser import FailureAnalyser, FailureReport
from auxilab_eval.loader import load_test_cases
from auxilab_eval.runners.base import AgentRunner, RunnerResult
from auxilab_eval.schema import TestCase

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class TestCaseResult:
    """Outcome of evaluating a single test case."""

    test_case: TestCase
    runner_result: RunnerResult
    evaluator_results: list[EvaluationResult] = field(default_factory=list)
    failure_report: Optional[FailureReport] = None
    passed: bool = False
    score: float = 0.0  # weighted aggregate of evaluator scores

    # ---- helpers ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.test_case.id,
            "description": self.test_case.description,
            "input": self.test_case.input,
            "expected": self.test_case.expected,
            "actual": self.runner_result.output,
            "duration_ms": self.runner_result.duration_ms,
            "runner_error": self.runner_result.error,
            "evaluators": [
                {
                    "evaluator": r.evaluator,
                    "passed": r.passed,
                    "score": r.score,
                    "weight": r.weight,
                    "detail": r.detail,
                    "breakdown": r.breakdown,
                }
                for r in self.evaluator_results
            ],
            "failure": self.failure_report.to_dict() if self.failure_report else None,
            "passed": self.passed,
            "score": self.score,
            "tags": list(self.test_case.tags),
        }


@dataclass
class EvalReport:
    """Aggregate report for a full evaluation run."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    agent_name: str
    results: list[TestCaseResult] = field(default_factory=list)

    # ---- aggregates ------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total) if self.total else 0.0

    @property
    def average_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def failure_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for r in self.results:
            if r.failure_report:
                key = r.failure_report.failure_type
                dist[key] = dist.get(key, 0) + 1
        return dist

    # ---- I/O -------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "failure_distribution": self.failure_distribution,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, path: PathLike) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8"
        )
        return path

    def to_html(self, path: PathLike, *, include_history: bool = True) -> Path:
        from auxilab_eval.reporter.html import render_html_report
        return render_html_report(self, path, include_history=include_history)

    def summary(self) -> str:
        lines = [
            f"Run {self.run_id} — agent={self.agent_name}",
            f"  total:        {self.total}",
            f"  passed:       {self.passed}",
            f"  failed:       {self.failed}",
            f"  pass rate:    {self.pass_rate:.0%}",
            f"  avg score:    {self.average_score:.2f}",
        ]
        if self.failure_distribution:
            lines.append("  failure types:")
            for ftype, count in sorted(
                self.failure_distribution.items(), key=lambda kv: -kv[1]
            ):
                lines.append(f"    - {ftype}: {count}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class EvalHarness:
    """End-to-end evaluator: run an agent against a set of test cases."""

    def __init__(
        self,
        runner: AgentRunner,
        test_cases: Union[PathLike, list[TestCase], list[dict]],
        *,
        analyse_failures: bool = True,
        failure_analyser: Optional[FailureAnalyser] = None,
        history_db: Optional[PathLike] = None,
    ) -> None:
        if not isinstance(runner, AgentRunner):
            raise TypeError(
                "runner must be an instance of AgentRunner "
                "(see auxilab_eval.runners)."
            )
        self.runner = runner
        self.test_cases: list[TestCase] = load_test_cases(test_cases)
        self.analyse_failures = analyse_failures
        self.failure_analyser = failure_analyser or FailureAnalyser()
        self.history_db = Path(history_db) if history_db else None

    # ---- main entry ------------------------------------------------------

    def run(self, *, only: Optional[Iterable[str]] = None) -> EvalReport:
        """Execute every test case (or a subset) and return an `EvalReport`.

        `only` filters by test case id.
        """
        wanted: Optional[set[str]] = set(only) if only else None
        started = datetime.now(timezone.utc)
        run_id = f"run-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        results: list[TestCaseResult] = []

        for tc in self.test_cases:
            if wanted is not None and tc.id not in wanted:
                continue
            results.append(self._run_one(tc))

        finished = datetime.now(timezone.utc)
        report = EvalReport(
            run_id=run_id,
            started_at=started,
            finished_at=finished,
            agent_name=self.runner.name,
            results=results,
        )
        self._persist_history(report)
        return report

    # ---- one test case ---------------------------------------------------

    def _run_one(self, tc: TestCase) -> TestCaseResult:
        runner_result = self.runner.run(tc.input)
        evaluator_results: list[EvaluationResult] = []

        if runner_result.ok:
            for spec in tc.evaluators:
                evaluator = get_evaluator(spec)
                try:
                    res = evaluator.evaluate(tc, runner_result.output)
                except Exception as exc:  # noqa: BLE001
                    res = EvaluationResult(
                        evaluator=f"{spec.type}:error",
                        passed=False,
                        score=0.0,
                        detail=f"Evaluator crashed: {exc}",
                        weight=spec.weight,
                    )
                evaluator_results.append(res)

        score = _weighted_score(evaluator_results)
        all_evals_passed = bool(evaluator_results) and all(
            r.passed for r in evaluator_results
        )
        passed = (
            runner_result.ok
            and all_evals_passed
            and score >= float(tc.pass_threshold)
        )

        failure_report: Optional[FailureReport] = None
        if not passed and self.analyse_failures:
            failure_report = self.failure_analyser.analyse(
                tc,
                actual_output=runner_result.output,
                evaluator_results=[
                    {
                        "evaluator": r.evaluator,
                        "passed": r.passed,
                        "score": r.score,
                        "detail": r.detail,
                    }
                    for r in evaluator_results
                ],
                runner_error=runner_result.error,
            )

        return TestCaseResult(
            test_case=tc,
            runner_result=runner_result,
            evaluator_results=evaluator_results,
            failure_report=failure_report,
            passed=passed,
            score=score,
        )

    # ---- history ---------------------------------------------------------

    def _persist_history(self, report: EvalReport) -> None:
        if self.history_db is None:
            return
        from auxilab_eval.reporter.store import HistoryStore
        store = HistoryStore(self.history_db)
        store.record(report)


def _weighted_score(results: list[EvaluationResult]) -> float:
    if not results:
        return 0.0
    total_weight = sum(max(r.weight, 0.0) for r in results)
    if total_weight <= 0:
        return sum(r.score for r in results) / len(results)
    return sum(r.score * max(r.weight, 0.0) for r in results) / total_weight
