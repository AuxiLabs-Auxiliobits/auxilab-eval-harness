"""Gradio web UI for auxilab-eval-harness.

Launch with:
    python app.py

Then open http://localhost:7860 in your browser.

Users can:
  1. Upload any .yaml / .yml test case file
  2. Pick an agent from the dropdown
  3. Hit "Run Evaluation" and see live results
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# Make the package importable whether or not `pip install -e .` was run
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

try:
    import gradio as gr
except ImportError:
    print("Gradio is not installed. Run:  pip install gradio>=4.0")
    sys.exit(1)

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from auxilab_eval.harness import EvalHarness
from auxilab_eval.loader import load_test_cases
from auxilab_eval.runners.python_runner import PythonRunner

load_dotenv()

# ---------------------------------------------------------------------------
# Agent registry — add your own agents here
# ---------------------------------------------------------------------------

def _load_agents() -> dict[str, Any]:
    """Import demo agents, skipping any that fail to import."""
    registry: dict[str, Any] = {}
    try:
        from demo.ap_exception_agent import handle_ap_exception
        registry["AP Exception Handler (ap_exception_agent.py)"] = handle_ap_exception
    except ImportError as exc:
        print(f"[warn] Could not load AP Exception agent: {exc}")

    try:
        from demo.payment_run_agent import run_payment
        registry["Payment Run Agent (payment_run_agent.py)"] = run_payment
    except ImportError as exc:
        print(f"[warn] Could not load Payment Run agent: {exc}")

    return registry


AGENT_REGISTRY = _load_agents()

AGENT_DESCRIPTIONS: dict[str, str] = {
    "AP Exception Handler (ap_exception_agent.py)": (
        "Classifies AP invoice exceptions into: approve, flag_duplicate, needs_review, reject.\n\n"
        "Required input fields: invoice_id, amount, vendor, due_date\n"
        "Optional input fields: po_number, duplicate_of, currency\n\n"
        "Use with: demo/test_cases/ap_exception_tests.yaml"
    ),
    "Payment Run Agent (payment_run_agent.py)": (
        "Processes payment run decisions: pay_now, hold, split_payment, defer, reject.\n\n"
        "Required input fields: payment_id, invoice_id, vendor, amount, currency, due_date, "
        "available_cash, batch_total_committed\n"
        "Optional input fields: vendor_tier, fraud_score, early_pay_discount_pct, early_pay_deadline\n\n"
        "Use with: demo/test_cases/payment_run_tests.yaml"
    ),
}

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = {"id", "input", "expected"}


def _validate_yaml_content(yaml_text: str) -> tuple[list[dict], str]:
    """Parse YAML and check basic structure. Returns (data, error_message).

    error_message is an empty string when everything is fine.
    """
    # 1. Parse YAML syntax
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        # Extract the useful part of the YAML error
        msg = str(exc)
        return [], (
            "**YAML syntax error** — the file could not be parsed.\n\n"
            f"```\n{msg}\n```\n\n"
            "Fix the YAML syntax and try again."
        )

    # 2. Not empty
    if data is None:
        return [], "**Empty file** — the uploaded file has no content."

    # 3. Must be a list
    if not isinstance(data, list):
        return [], (
            f"**Wrong structure** — expected a list of test cases at the top level "
            f"but got `{type(data).__name__}`.\n\n"
            "Every test case file must look like:\n"
            "```yaml\n- id: my_test\n  input: ...\n  expected: ...\n```"
        )

    # 4. Non-empty list
    if len(data) == 0:
        return [], "**Empty list** — the file parses correctly but contains zero test cases."

    # 5. Each item must be a dict with required keys
    item_errors: list[str] = []
    for i, item in enumerate(data):
        label = f"Item {i + 1}"
        if not isinstance(item, dict):
            item_errors.append(f"- {label}: expected a mapping, got `{type(item).__name__}`")
            continue
        label = f"Item {i + 1} (`{item.get('id', '?')}`)"
        missing = _REQUIRED_FIELDS - item.keys()
        if missing:
            item_errors.append(
                f"- {label}: missing required field(s): "
                + ", ".join(f"`{f}`" for f in sorted(missing))
            )

    if item_errors:
        return [], (
            f"**Schema errors** in {len(item_errors)} test case(s):\n\n"
            + "\n".join(item_errors)
            + "\n\nEvery test case must have: `id`, `input`, `expected`."
        )

    return data, ""


# ---------------------------------------------------------------------------
# Core evaluation function (called by Gradio)
# ---------------------------------------------------------------------------

# Persistent temp dir for HTML reports (lives for the duration of the server process)
_REPORT_DIR = Path(tempfile.mkdtemp(prefix="auxilab_eval_ui_"))


def run_evaluation(
    yaml_filepath: str | None,
    agent_name: str | None,
) -> tuple[str, list[list[str]], str, str, str | None]:
    """Run the harness and return (summary_md, table_rows, json_detail, error_md, html_path).

    html_path is the path to the generated HTML report, or None on error.
    All five outputs are always returned so Gradio can update all components.
    """
    empty = ("", [], "{}", "")

    _no_html: str | None = None  # returned on all error paths

    # ── Guard: nothing uploaded ──────────────────────────────────────────────
    if yaml_filepath is None or str(yaml_filepath).strip() == "":
        return (
            "", [], "{}",
            "### ❌ No file uploaded\n\n"
            "Please attach a `.yaml` or `.yml` test cases file using the upload box.",
            _no_html,
        )

    # ── Guard: file extension ────────────────────────────────────────────────
    path = Path(yaml_filepath)
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return (
            "", [], "{}",
            f"### ❌ Wrong file type: `{path.suffix or '(none)'}`\n\n"
            "Only `.yaml` and `.yml` files are accepted.\n\n"
            "Rename your file or export it as YAML.",
            _no_html,
        )

    # ── Guard: no agent ──────────────────────────────────────────────────────
    if not agent_name or agent_name.strip() == "":
        return (
            "", [], "{}",
            "### ❌ No agent selected\n\n"
            "Please choose an agent from the dropdown.\n\n"
            "**Available agents:**\n"
            + "".join(f"- `{k}`\n" for k in AGENT_REGISTRY),
            _no_html,
        )

    if agent_name not in AGENT_REGISTRY:
        return (
            "", [], "{}",
            f"### ❌ Unknown agent: `{agent_name}`\n\n"
            "The selected agent is not registered.\n\n"
            "**Available agents:**\n"
            + "".join(f"- `{k}`\n" for k in AGENT_REGISTRY),
            _no_html,
        )

    # ── Read file ────────────────────────────────────────────────────────────
    try:
        yaml_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "", [], "{}",
            f"### ❌ Could not read file\n\n```\n{exc}\n```",
            _no_html,
        )

    # ── Validate YAML structure ──────────────────────────────────────────────
    raw_data, structural_error = _validate_yaml_content(yaml_text)
    if structural_error:
        return ("", [], "{}", f"### ❌ Invalid test case file\n\n{structural_error}", _no_html)

    # ── Load + Pydantic validate ─────────────────────────────────────────────
    try:
        test_cases = load_test_cases(raw_data)
    except ValidationError as exc:
        lines = []
        for err in exc.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            lines.append(f"- `{loc}`: {err['msg']}")
        return (
            "", [], "{}",
            "### ❌ Test case schema validation failed\n\n"
            f"{len(exc.errors())} error(s) found:\n\n"
            + "\n".join(lines)
            + "\n\nCheck that all evaluator specs and field types are correct.",
            _no_html,
        )
    except Exception as exc:
        return (
            "", [], "{}",
            f"### ❌ Failed to load test cases\n\n```\n{exc}\n```",
            _no_html,
        )

    # ── Run the harness ──────────────────────────────────────────────────────
    agent_fn = AGENT_REGISTRY[agent_name]
    agent_label = agent_name.split("(")[0].strip()
    runner = PythonRunner(agent_fn, name=agent_label)

    try:
        harness = EvalHarness(runner=runner, test_cases=test_cases)
        report = harness.run()
    except TypeError as exc:
        return (
            "", [], "{}",
            "### ❌ Agent / test case mismatch\n\n"
            "The agent raised a `TypeError` — this usually means the `input` fields "
            "in your YAML don't match what the selected agent expects.\n\n"
            f"```\n{exc}\n```\n\n"
            f"**Tip:** Make sure you're using test cases designed for "
            f"**{agent_label}**. Check the agent description for the required input fields.",
            _no_html,
        )
    except Exception:
        return (
            "", [], "{}",
            "### ❌ Evaluation error\n\n"
            f"```\n{traceback.format_exc()}\n```",
            _no_html,
        )

    # ── Build results table ──────────────────────────────────────────────────
    table_rows: list[list[str]] = []
    for r in report.results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        score_str = f"{r.score * 100:.0f}%"
        dur_str = (
            f"{r.runner_result.duration_ms:.1f} ms"
            if r.runner_result.duration_ms is not None
            else "—"
        )
        failure_str = (
            r.failure_report.failure_type if r.failure_report else ""
        )
        runner_err = r.runner_result.error or ""
        table_rows.append([
            r.test_case.id,
            r.test_case.description or "",
            status,
            score_str,
            dur_str,
            failure_str or runner_err,
        ])

    # ── Summary markdown ─────────────────────────────────────────────────────
    if report.pass_rate >= 0.9:
        icon = "🟢"
    elif report.pass_rate >= 0.75:
        icon = "🟡"
    else:
        icon = "🔴"

    durations = [r.runner_result.duration_ms for r in report.results
                 if r.runner_result.duration_ms is not None]
    avg_lat = sum(durations) / len(durations) if durations else 0

    summary_md = (
        f"### {icon} Evaluation complete — {agent_label}\n\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| **Tests run** | {report.total} |\n"
        f"| **Passed** | {report.passed} |\n"
        f"| **Failed** | {report.failed} |\n"
        f"| **Pass rate** | {report.pass_rate:.1%} |\n"
        f"| **Avg score** | {report.average_score:.3f} |\n"
        f"| **Avg latency** | {avg_lat:.1f} ms |\n"
        f"| **Run ID** | `{report.run_id}` |\n"
    )

    if report.failure_distribution:
        summary_md += "\n**Failure breakdown:**\n"
        for ftype, count in sorted(
            report.failure_distribution.items(), key=lambda x: -x[1]
        ):
            summary_md += f"- `{ftype}`: {count}\n"

    # ── Full JSON detail ─────────────────────────────────────────────────────
    json_detail = json.dumps(report.to_dict(), indent=2, default=str)

    # ── Generate HTML report for download ────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = agent_label.replace(" ", "_").replace("/", "-")
    html_filename = f"{safe_label}_{timestamp}.html"
    html_path = str(_REPORT_DIR / html_filename)
    try:
        report.to_html(html_path, include_history=False)
    except Exception:
        html_path = None  # report still shown in UI; download simply unavailable

    return summary_md, table_rows, json_detail, "", html_path


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def _build_app() -> Any:
    if not AGENT_REGISTRY:
        print(
            "[error] No agents loaded. Make sure `demo/` is on the path "
            "and both agent files import correctly."
        )

    agent_choices = list(AGENT_REGISTRY.keys())

    with gr.Blocks(
        title="auxilab-eval - AI Agent Test Harness",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate"),
    ) as app:

        # ── Header ──────────────────────────────────────────────────────────
        gr.Markdown(
            "# 🧪 auxilab-eval - AI Agent Test Harness\n"
            "Upload a YAML test suite, select an agent, and run a full evaluation."
        )

        with gr.Row():

            # ── Left panel: inputs ───────────────────────────────────────────
            with gr.Column(scale=1, min_width=320):

                gr.Markdown("### 1️⃣  Upload Test Cases")
                yaml_file = gr.File(
                    label="Test cases (.yaml / .yml)",
                    file_types=[".yaml", ".yml"],
                    type="filepath",
                )
                gr.Markdown(
                    "_Not sure about the format? "
                    "See `demo/test_cases/ap_exception_tests.yaml` for an example._",
                    visible=True,
                )

                gr.Markdown("### 2️⃣  Select Agent")
                agent_dropdown = gr.Dropdown(
                    choices=agent_choices,
                    label="Agent",
                    value=None,
                    interactive=True,
                    info="Choose the agent function to evaluate against.",
                )
                agent_info = gr.Textbox(
                    label="Agent info",
                    value="Select an agent to see its description.",
                    interactive=False,
                    lines=5,
                )

                gr.Markdown("### 3️⃣  Run")
                run_btn = gr.Button(
                    "▶  Run Evaluation",
                    variant="primary",
                    size="lg",
                )
                gr.Markdown(
                    "_Results appear on the right. "
                    "The full JSON detail is available in the expandable section below the table._"
                )

            # ── Right panel: outputs ─────────────────────────────────────────
            with gr.Column(scale=2):

                error_box = gr.Markdown(
                    value="",
                    label="Errors",
                    elem_classes=["error-box"],
                    visible=False,
                )
                summary_box = gr.Markdown(
                    value="",
                    label="Summary",
                    elem_classes=["summary-box"],
                    visible=False,
                )

                download_btn = gr.File(
                    label="📥 Download HTML Report",
                    visible=False,
                    interactive=False,
                )

                gr.Markdown("### 📊 Test Results")
                results_table = gr.Dataframe(
                    headers=[
                        "Test ID",
                        "Description",
                        "Status",
                        "Score",
                        "Duration",
                        "Failure / Error",
                    ],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    interactive=False,
                    wrap=True,
                    row_count=(1, "dynamic"),
                )

        with gr.Accordion("📄 Full JSON Output", open=False):
            json_output = gr.Code(
                language="json",
                label="Detailed results (all test cases)",
                value="{}",
            )

        # ── Built-in examples ────────────────────────────────────────────────
        _ap_yaml = str((_ROOT / "demo" / "test_cases" / "ap_exception_tests.yaml").resolve())
        _pr_yaml = str((_ROOT / "demo" / "test_cases" / "payment_run_tests.yaml").resolve())

        if agent_choices:
            gr.Markdown("---\n### 📁 Quick Start — Built-in Examples")
            gr.Examples(
                examples=[
                    [_ap_yaml, agent_choices[0]] if len(agent_choices) > 0 else [],
                    [_pr_yaml, agent_choices[1]] if len(agent_choices) > 1 else [],
                ],
                inputs=[yaml_file, agent_dropdown],
                label="Click a row to load a built-in example, then press Run",
            )

        # ── Interactions ─────────────────────────────────────────────────────

        def _on_agent_change(name: str | None) -> str:
            if not name:
                return "Select an agent to see its description."
            return AGENT_DESCRIPTIONS.get(name, "No description available.")

        def _run_and_show(
            yaml_filepath: str | None,
            agent_name: str | None,
        ) -> tuple[Any, Any, Any, Any, Any]:
            summary, table, json_str, error, html_path = run_evaluation(
                yaml_filepath, agent_name
            )
            has_error = bool(error)
            has_summary = bool(summary)
            return (
                gr.update(value=error, visible=has_error),          # error_box
                gr.update(value=summary, visible=has_summary),      # summary_box
                table,                                               # results_table
                json_str,                                            # json_output
                gr.update(value=html_path, visible=html_path is not None),  # download_btn
            )

        agent_dropdown.change(
            fn=_on_agent_change,
            inputs=[agent_dropdown],
            outputs=[agent_info],
        )

        run_btn.click(
            fn=_run_and_show,
            inputs=[yaml_file, agent_dropdown],
            outputs=[error_box, summary_box, results_table, json_output, download_btn],
        )

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not AGENT_REGISTRY:
        print(
            "Warning: no agents were loaded. "
            "Make sure you run this from the project root:\n"
            "    python app.py"
        )

    ui = _build_app()
    ui.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
    )
