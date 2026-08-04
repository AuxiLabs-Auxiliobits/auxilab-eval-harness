"""Reporting subpackage — HTML, Matplotlib charts, SQLite history."""

from auxilab_eval.reporter.html import render_html_report
from auxilab_eval.reporter.charts import (
    render_failure_distribution_chart,
    render_pass_rate_trend_chart,
)
from auxilab_eval.reporter.store import HistoryStore

__all__ = [
    "render_html_report",
    "render_failure_distribution_chart",
    "render_pass_rate_trend_chart",
    "HistoryStore",
]
