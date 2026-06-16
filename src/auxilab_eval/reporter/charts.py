"""Matplotlib charts rendered as base64-embedded PNGs for the HTML report."""

from __future__ import annotations

import base64
import io
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless backend — must be set before pyplot import
import matplotlib.pyplot as plt  # noqa: E402


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_failure_distribution_chart(distribution: dict[str, int]) -> Optional[str]:
    """Bar chart of failure types -> count. Returns base64-encoded PNG."""
    if not distribution:
        return None
    labels = list(distribution.keys())
    counts = [distribution[k] for k in labels]
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    bars = ax.bar(labels, counts, color="#d4654c", edgecolor="#8a3c2a")
    ax.set_title("Failure type distribution", fontsize=13, weight="bold")
    ax.set_ylabel("Count")
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.05,
            str(count),
            ha="center",
            va="bottom",
            fontsize=10,
        )
    return _fig_to_b64(fig)


def render_pass_rate_trend_chart(history) -> Optional[str]:
    """Line chart of pass rate over historical runs (oldest -> newest)."""
    if not history or len(history) < 2:
        return None
    labels = [h.run_id.split("-")[1][-6:] for h in history]
    rates = [h.pass_rate * 100 for h in history]
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.plot(labels, rates, marker="o", color="#2c7a4d", linewidth=2)
    ax.fill_between(labels, rates, alpha=0.15, color="#2c7a4d")
    ax.set_ylim(0, 105)
    ax.set_title("Pass rate trend", fontsize=13, weight="bold")
    ax.set_ylabel("Pass rate (%)")
    ax.set_xlabel("Run")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
    return _fig_to_b64(fig)


def render_score_per_case_chart(results) -> Optional[str]:
    """Per-test-case aggregate score, coloured by pass/fail."""
    if not results:
        return None
    labels = [r.test_case.id for r in results]
    scores = [r.score for r in results]
    colours = ["#2c7a4d" if r.passed else "#d4654c" for r in results]
    fig, ax = plt.subplots(figsize=(max(7.5, len(labels) * 0.45), 4.0))
    ax.bar(labels, scores, color=colours, edgecolor="#333")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.7, color="#888", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_title("Score per test case", fontsize=13, weight="bold")
    ax.set_ylabel("Aggregate score")
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    return _fig_to_b64(fig)
