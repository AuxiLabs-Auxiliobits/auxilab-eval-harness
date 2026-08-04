"""HTML report renderer (Jinja2)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from auxilab_eval.reporter.charts import (
    render_failure_distribution_chart,
    render_pass_rate_trend_chart,
    render_score_per_case_chart,
)


_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["pretty_json"] = _pretty_json
    env.filters["pct"] = lambda v: f"{(v or 0) * 100:.1f}%"
    env.filters["score"] = lambda v: f"{(v or 0):.2f}"
    return env


def _pretty_json(value: Any) -> str:
    if value is None:
        return ""
    try:
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)
    except TypeError:
        return str(value)


def render_html_report(
    report,
    out_path: Path | str,
    *,
    include_history: bool = True,
) -> Path:
    """Render `report` to a self-contained HTML file."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    failure_chart = render_failure_distribution_chart(report.failure_distribution)
    score_chart = render_score_per_case_chart(report.results)

    history_chart: Optional[str] = None
    if include_history:
        db_env = os.getenv("AUXILAB_EVAL_DB")
        # Only attempt history rendering when a DB exists.
        candidate = Path(db_env) if db_env else None
        if candidate and candidate.exists():
            try:
                from auxilab_eval.reporter.store import HistoryStore
                history = HistoryStore(candidate).history(
                    agent_name=report.agent_name, limit=20
                )
                history_chart = render_pass_rate_trend_chart(history)
            except Exception:  # noqa: BLE001 - history is best-effort
                history_chart = None

    template = _env().get_template("report.html.j2")
    html = template.render(
        report=report,
        failure_chart=failure_chart,
        score_chart=score_chart,
        history_chart=history_chart,
    )
    out_path.write_text(html, encoding="utf-8")
    return out_path
