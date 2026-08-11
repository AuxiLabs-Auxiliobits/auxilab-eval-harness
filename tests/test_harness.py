"""End-to-end harness tests that exercise the full pipeline without any
network calls (LLM-judge / failure analyser are disabled).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from auxilab_eval import EvalHarness, PythonRunner, load_test_cases
from auxilab_eval.harness import EvalReport
from auxilab_eval.reporter.store import HistoryStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def yaml_suite(tmp_path: Path) -> Path:
    """A small in-tmpdir YAML suite with three test cases."""
    suite = tmp_path / "suite.yaml"
    suite.write_text(
        """
- id: case_pass
  description: Echo agent returns the expected value
  input: {x: 10}
  expected: {echo: 10}
  evaluators:
    - type: exact
      field: echo

- id: case_regex
  description: Reason text matches a regex
  input: {x: 1}
  expected: {}
  evaluators:
    - type: regex
      field: message
      pattern: "(?i)success"

- id: case_fail
  description: Intentional mismatch to exercise the failure path
  input: {x: 5}
  expected: {echo: 999}
  evaluators:
    - type: exact
      field: echo
""",
        encoding="utf-8",
    )
    return suite


def _echo_agent(payload: dict) -> dict:
    """Agent: echo x back and add a friendly message."""
    return {"echo": payload.get("x"), "message": "Operation completed successfully."}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_loader_parses_yaml_suite(yaml_suite: Path):
    cases = load_test_cases(yaml_suite)
    assert len(cases) == 3
    assert [c.id for c in cases] == ["case_pass", "case_regex", "case_fail"]
    assert cases[0].evaluators[0].type == "exact"


def test_harness_runs_end_to_end_and_aggregates(yaml_suite: Path):
    harness = EvalHarness(
        runner=PythonRunner(_echo_agent, name="echo_agent"),
        test_cases=yaml_suite,
        analyse_failures=False,  # no network
    )
    report = harness.run()

    assert isinstance(report, EvalReport)
    assert report.total == 3
    assert report.passed == 2
    assert report.failed == 1
    assert 0.0 < report.pass_rate < 1.0
    assert report.agent_name == "echo_agent"

    by_id = {r.test_case.id: r for r in report.results}
    assert by_id["case_pass"].passed is True
    assert by_id["case_regex"].passed is True
    assert by_id["case_fail"].passed is False


def test_harness_writes_html_and_json_reports(tmp_path: Path, yaml_suite: Path):
    harness = EvalHarness(
        runner=PythonRunner(_echo_agent),
        test_cases=yaml_suite,
        analyse_failures=False,
    )
    report = harness.run()

    html_path = report.to_html(tmp_path / "report.html")
    json_path = report.to_json(tmp_path / "report.json")

    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "Evaluation Report" in html
    assert "case_pass" in html
    assert "case_fail" in html

    assert json_path.exists()
    assert '"pass_rate"' in json_path.read_text(encoding="utf-8")


def test_harness_persists_run_history_to_sqlite(tmp_path: Path, yaml_suite: Path):
    db_path = tmp_path / "history.sqlite"
    harness = EvalHarness(
        runner=PythonRunner(_echo_agent, name="echo_agent"),
        test_cases=yaml_suite,
        analyse_failures=False,
        history_db=db_path,
    )
    report1 = harness.run()
    report2 = harness.run()

    assert db_path.exists()
    store = HistoryStore(db_path)
    history = store.history(agent_name="echo_agent")
    assert len(history) == 2
    ids = {h.run_id for h in history}
    assert {report1.run_id, report2.run_id}.issubset(ids)


def test_failure_analyser_heuristic_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch, yaml_suite: Path,
):
    # Force the analyser to fall back to its heuristic path.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    harness = EvalHarness(
        runner=PythonRunner(_echo_agent),
        test_cases=yaml_suite,
        analyse_failures=True,
    )
    report = harness.run()
    failing = [r for r in report.results if not r.passed]
    assert failing, "expected at least one failure to analyse"
    fr = failing[0].failure_report
    assert fr is not None
    assert fr.failure_type  # always populated by the heuristic fallback
    assert fr.error and "heuristic" in fr.error
