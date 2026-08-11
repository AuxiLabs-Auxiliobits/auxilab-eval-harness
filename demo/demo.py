"""End-to-end demo for auxilab-eval-harness.

Two modes:

    python demo/demo.py                # CLI: prints a scorecard + writes HTML
    python demo/demo.py --gradio       # interactive Gradio UI

Targets the mock AP Exception Handling Agent in `demo/ap_exception_agent.py`
and runs the 10 YAML test cases under `demo/test_cases/`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make `demo/` importable when running as a script.
_DEMO_DIR = Path(__file__).resolve().parent
if str(_DEMO_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_DEMO_DIR.parent))
if str(_DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(_DEMO_DIR))

# Make `src/` importable for in-tree development.
_SRC = _DEMO_DIR.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from auxilab_eval import EvalHarness, PythonRunner  # noqa: E402
from ap_exception_agent import handle_ap_exception  # noqa: E402

TEST_CASES_PATH = _DEMO_DIR / "test_cases" / "ap_exception_tests.yaml"
DEFAULT_HTML_PATH = _DEMO_DIR.parent / "reports" / "ap_exception_report.html"
DEFAULT_DB_PATH = _DEMO_DIR.parent / ".auxilab_eval" / "history.sqlite"


# ---------------------------------------------------------------------------
# CLI mode
# ---------------------------------------------------------------------------


def run_cli(html_path: Path, db_path: Path | None, no_llm: bool) -> int:
    if db_path:
        os.environ.setdefault("AUXILAB_EVAL_DB", str(db_path))

    print("=" * 72)
    print("auxilab-eval — demo run against AP Exception Handling Agent")
    print("=" * 72)
    print(f"Test cases: {TEST_CASES_PATH}")
    print(f"Agent:      demo.ap_exception_agent:handle_ap_exception")
    print(f"LLM judge:  {'disabled' if no_llm else 'enabled (Claude)'}")
    print()

    harness = EvalHarness(
        runner=PythonRunner(handle_ap_exception, name="ap_exception_agent"),
        test_cases=TEST_CASES_PATH,
        analyse_failures=not no_llm,
        history_db=db_path,
    )
    report = harness.run()

    # Per-case scorecard
    print(f"{'ID':<32} {'Status':<7} {'Score':<7} {'Failure type':<24}")
    print("-" * 72)
    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        ftype = r.failure_report.failure_type if r.failure_report else ""
        print(f"{r.test_case.id:<32} {status:<7} {r.score:<7.2f} {ftype:<24}")
    print()
    print(report.summary())

    html = report.to_html(html_path)
    print(f"\nHTML report written to {html}")
    return 0 if report.failed == 0 else 1


# ---------------------------------------------------------------------------
# Gradio mode
# ---------------------------------------------------------------------------


def run_gradio(db_path: Path | None) -> None:
    try:
        import gradio as gr  # type: ignore
    except ImportError:
        print(
            "Gradio is not installed. Install it with:\n"
            "  pip install auxilab-eval[gradio]\n"
            "or `pip install gradio`."
        )
        sys.exit(1)

    if db_path:
        os.environ.setdefault("AUXILAB_EVAL_DB", str(db_path))

    def _execute(no_llm: bool):
        harness = EvalHarness(
            runner=PythonRunner(handle_ap_exception, name="ap_exception_agent"),
            test_cases=TEST_CASES_PATH,
            analyse_failures=not no_llm,
            history_db=db_path,
        )
        report = harness.run()

        rows = []
        for r in report.results:
            rows.append([
                r.test_case.id,
                "✅ PASS" if r.passed else "❌ FAIL",
                f"{r.score:.2f}",
                r.failure_report.failure_type if r.failure_report else "—",
                (r.failure_report.summary if r.failure_report else "") or "",
            ])

        # Failure-type breakdown as a tiny string the UI can render.
        dist_lines = [
            f"- **{k}**: {v}"
            for k, v in sorted(
                report.failure_distribution.items(), key=lambda kv: -kv[1]
            )
        ]
        breakdown_md = "\n".join(dist_lines) or "_No failures._"

        # Always emit HTML (so user can download).
        html_path = DEFAULT_HTML_PATH
        report.to_html(html_path)

        summary_md = (
            f"### Run `{report.run_id}`\n"
            f"- Total: **{report.total}**\n"
            f"- Passed: **{report.passed}**\n"
            f"- Failed: **{report.failed}**\n"
            f"- Pass rate: **{report.pass_rate:.0%}**\n"
            f"- Avg score: **{report.average_score:.2f}**\n"
        )
        return summary_md, rows, breakdown_md, str(html_path)

    with gr.Blocks(title="auxilab-eval demo") as ui:
        gr.Markdown(
            "# auxilab-eval — AP Exception Handling Agent demo\n"
            "Runs 10 YAML test cases against the mock AP agent and produces a "
            "pass/fail scorecard, failure-type breakdown, and a downloadable "
            "HTML report."
        )
        with gr.Row():
            no_llm = gr.Checkbox(
                value=False,
                label="Disable LLM-as-judge / failure analyser (offline mode)",
            )
            run_btn = gr.Button("Run evaluation", variant="primary")

        summary = gr.Markdown()
        table = gr.Dataframe(
            headers=["Test ID", "Status", "Score", "Failure type", "Failure summary"],
            datatype=["str", "str", "str", "str", "str"],
            interactive=False,
        )
        breakdown = gr.Markdown(label="Failure distribution")
        html_file = gr.File(label="HTML report")

        run_btn.click(
            fn=_execute,
            inputs=[no_llm],
            outputs=[summary, table, breakdown, html_file],
        )

    ui.launch()


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="auxilab-eval demo")
    parser.add_argument(
        "--gradio",
        action="store_true",
        help="Launch the Gradio UI instead of running once on the CLI.",
    )
    parser.add_argument(
        "--html",
        default=str(DEFAULT_HTML_PATH),
        help="HTML report output path (CLI mode).",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite history DB path (set empty string to disable).",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip the LLM judge / failure analyser (no API key required).",
    )
    args = parser.parse_args()

    db_path: Path | None = Path(args.db) if args.db else None

    if args.gradio:
        run_gradio(db_path)
        return 0
    return run_cli(Path(args.html), db_path, args.no_llm)


if __name__ == "__main__":
    sys.exit(main())
