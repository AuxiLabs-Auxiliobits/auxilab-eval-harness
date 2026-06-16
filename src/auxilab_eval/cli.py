"""`auxilab-eval` command-line interface.

Examples:

    # Run a YAML suite against a Python callable located at "demo.agent.run"
    auxilab-eval run --tests tests.yaml --agent demo.agent:run --html report.html

    # Run against a remote HTTP endpoint
    auxilab-eval run --tests tests.yaml --http http://localhost:8000/invoke

    # Show the last 10 runs from the history DB
    auxilab-eval history --limit 10
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from auxilab_eval import EvalHarness, HttpRunner, PythonRunner

# Load .env if present so the CLI picks up ANTHROPIC_API_KEY etc.
load_dotenv()


@click.group()
@click.version_option(package_name="auxilab-eval")
def main() -> None:
    """auxilab-eval — evaluation harness for agentic AI."""


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@main.command()
@click.option("--tests", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Path to a .yaml/.yml/.json test case file.")
@click.option("--agent", "agent_ref", default=None,
              help="Python entry point in `module:attr` form for a callable agent.")
@click.option("--http", "http_url", default=None,
              help="Run against a remote HTTP agent endpoint.")
@click.option("--html", "html_out", default=None,
              type=click.Path(dir_okay=False),
              help="Write an HTML report to this path.")
@click.option("--json", "json_out", default=None,
              type=click.Path(dir_okay=False),
              help="Write a JSON report to this path.")
@click.option("--no-llm", is_flag=True, default=False,
              help="Skip LLM-based failure analysis.")
@click.option("--history-db", default=None, type=click.Path(dir_okay=False),
              help="SQLite DB to record this run in (overrides AUXILAB_EVAL_DB).")
def run(
    tests: str,
    agent_ref: Optional[str],
    http_url: Optional[str],
    html_out: Optional[str],
    json_out: Optional[str],
    no_llm: bool,
    history_db: Optional[str],
) -> None:
    """Run an evaluation suite against an agent."""
    if bool(agent_ref) == bool(http_url):
        raise click.UsageError("Provide exactly one of --agent or --http.")

    if agent_ref:
        runner = PythonRunner(_import_callable(agent_ref))
    else:
        runner = HttpRunner(http_url)  # type: ignore[arg-type]

    db = history_db or os.getenv("AUXILAB_EVAL_DB")
    harness = EvalHarness(
        runner=runner,
        test_cases=tests,
        analyse_failures=not no_llm,
        history_db=db,
    )
    report = harness.run()
    click.echo(report.summary())

    if json_out:
        path = report.to_json(json_out)
        click.echo(f"\nJSON report -> {path}")
    if html_out:
        path = report.to_html(html_out)
        click.echo(f"HTML report -> {path}")

    sys.exit(0 if report.failed == 0 else 1)


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------


@main.command()
@click.option("--db", default=None, type=click.Path(dir_okay=False),
              help="SQLite history DB (defaults to AUXILAB_EVAL_DB).")
@click.option("--agent", default=None, help="Filter by agent name.")
@click.option("--limit", default=20, type=int, help="Maximum runs to show.")
def history(db: Optional[str], agent: Optional[str], limit: int) -> None:
    """Show past runs recorded in the history database."""
    from auxilab_eval.reporter.store import HistoryStore

    db_path = db or os.getenv("AUXILAB_EVAL_DB")
    if not db_path:
        raise click.UsageError(
            "No history DB. Pass --db or set AUXILAB_EVAL_DB."
        )
    if not Path(db_path).exists():
        raise click.UsageError(f"History DB does not exist: {db_path}")

    runs = HistoryStore(db_path).history(agent_name=agent, limit=limit)
    if not runs:
        click.echo("No runs recorded.")
        return
    click.echo(f"{'started_at':<27} {'agent':<22} {'pass':<6} {'rate':<6} run_id")
    for r in runs:
        click.echo(
            f"{r.started_at:<27} {r.agent_name[:22]:<22} "
            f"{r.passed}/{r.total:<4} {r.pass_rate*100:5.1f}% {r.run_id}"
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _import_callable(ref: str):
    """Import `module:attr` (or `module.attr`) and return the callable."""
    if ":" in ref:
        module_name, attr = ref.split(":", 1)
    elif "." in ref:
        module_name, attr = ref.rsplit(".", 1)
    else:
        raise click.UsageError(
            f"Invalid --agent reference: {ref!r}. Use `module:attr`."
        )

    # Make CWD importable so users can reference local demo modules.
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise click.UsageError(f"Could not import {module_name!r}: {exc}") from exc

    if not hasattr(module, attr):
        raise click.UsageError(f"{module_name!r} has no attribute {attr!r}.")
    fn = getattr(module, attr)
    if not callable(fn):
        raise click.UsageError(f"{ref!r} is not callable.")
    return fn


if __name__ == "__main__":  # pragma: no cover
    main()
