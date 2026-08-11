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


def _format_summary(report) -> str:
    """Format a rich CLI summary of the evaluation report."""
    total = report.total
    passed = report.passed
    failed = report.failed
    pass_rate = report.pass_rate
    
    # Color codes for terminal
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    
    output = [
        "",
        f"{BOLD}{BLUE}╔══════════════════════════════════════════╗{RESET}",
        f"{BOLD}{BLUE}║  Evaluation Complete{' ' * 18}║{RESET}",
        f"{BOLD}{BLUE}╚══════════════════════════════════════════╝{RESET}",
        "",
        f"  Agent:         {BOLD}{report.agent_name}{RESET}",
        f"  Run ID:        {report.run_id}",
        "",
        f"  Results:",
        f"    {GREEN}✓ Passed:{RESET:>8} {BOLD}{passed}{RESET}/{total}",
        f"    {RED}✗ Failed:{RESET:>8} {BOLD}{failed}{RESET}/{total}",
        f"    Pass Rate:  {BOLD}{pass_rate:.1%}{RESET}",
        f"    Avg Score:  {BOLD}{report.average_score:.2f}{RESET}",
        "",
    ]
    
    # Show failure breakdown if there are failures
    if failed > 0 and report.failure_distribution:
        output.append("  Failure Breakdown:")
        for failure_type, count in report.failure_distribution.items():
            pct = (count / failed) * 100
            output.append(f"    • {failure_type}: {count} ({pct:.0f}%)")
        output.append("")
    
    # Performance metrics
    if report.results:
        avg_latency = sum(r.runner_result.duration_ms for r in report.results) / len(report.results)
        min_latency = min(r.runner_result.duration_ms for r in report.results)
        max_latency = max(r.runner_result.duration_ms for r in report.results)
        
        output.append("  Performance:")
        output.append(f"    Avg Latency:  {avg_latency:.1f} ms")
        output.append(f"    Min Latency:  {min_latency:.1f} ms")
        output.append(f"    Max Latency:  {max_latency:.1f} ms")
        output.append("")
    
    # Overall status
    if pass_rate == 1.0:
        output.append(f"  {GREEN}{BOLD}🎉 All tests passed!{RESET}")
    elif pass_rate >= 0.75:
        output.append(f"  {YELLOW}{BOLD}⚠️  Good performance, but some tests failed{RESET}")
    else:
        output.append(f"  {RED}{BOLD}❌ Multiple test failures - review needed{RESET}")
    
    output.append("")
    return "\n".join(output)


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
@click.option("--csv", "csv_out", default=None,
              type=click.Path(dir_okay=False),
              help="Write a CSV export to this path.")
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
    csv_out: Optional[str],
    no_llm: bool,
    history_db: Optional[str],
) -> None:
    """Run an evaluation suite against an agent."""
    if bool(agent_ref) == bool(http_url):
        raise click.UsageError("Provide exactly one of --agent or --http.")

    click.echo("\n" + "=" * 50)
    click.echo("  auxilab-eval — Starting evaluation")
    click.echo("=" * 50 + "\n")
    
    if agent_ref:
        click.echo(f"  📦 Loading agent: {agent_ref}")
        runner = PythonRunner(_import_callable(agent_ref))
    else:
        click.echo(f"  🌐 Using HTTP endpoint: {http_url}")
        runner = HttpRunner(http_url)  # type: ignore[arg-type]

    click.echo(f"  📋 Loading test cases: {tests}\n")
    
    db = history_db or os.getenv("AUXILAB_EVAL_DB")
    harness = EvalHarness(
        runner=runner,
        test_cases=tests,
        analyse_failures=not no_llm,
        history_db=db,
    )
    
    click.echo("  ⏱️  Running tests...\n")
    try:
        report = harness.run()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"\n  ❌ Evaluation failed: {exc}", err=True)
        sys.exit(2)

    # Print rich summary
    click.echo(_format_summary(report))

    if json_out:
        path = report.to_json(json_out)
        click.echo(f"  📄 JSON report → {path}")
    if html_out:
        path = report.to_html(html_out)
        click.echo(f"  🌐 HTML report → {path}")
    if csv_out:
        path = report.to_csv(csv_out)
        click.echo(f"  📊 CSV export → {path}")
    
    click.echo("")

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
        click.echo("📭 No runs recorded.")
        return
    
    click.echo("\n" + "=" * 80)
    click.echo("  Run History")
    click.echo("=" * 80 + "\n")
    
    click.echo(f"{'Started':<27} {'Agent':<25} {'Pass':<8} {'Rate':<8} {'Run ID':<36}")
    click.echo("-" * 104)
    
    for r in runs:
        rate_pct = f"{r.pass_rate*100:5.1f}%"
        pass_str = f"{r.passed}/{r.total}"
        
        # Color code the pass rate
        if r.pass_rate == 1.0:
            rate_display = f"\033[92m{rate_pct}\033[0m"
        elif r.pass_rate >= 0.75:
            rate_display = f"\033[93m{rate_pct}\033[0m"
        else:
            rate_display = f"\033[91m{rate_pct}\033[0m"
        
        click.echo(
            f"{r.started_at:<27} {r.agent_name[:25]:<25} {pass_str:<8} "
            f"{rate_display:<8} {r.run_id}"
        )
    
    click.echo("\n")


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
