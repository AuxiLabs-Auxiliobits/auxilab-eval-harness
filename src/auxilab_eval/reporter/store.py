"""SQLite-backed run history store."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    agent_name    TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT NOT NULL,
    total         INTEGER NOT NULL,
    passed        INTEGER NOT NULL,
    failed        INTEGER NOT NULL,
    pass_rate     REAL NOT NULL,
    average_score REAL NOT NULL,
    summary_json  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_results (
    run_id      TEXT NOT NULL,
    test_id     TEXT NOT NULL,
    passed      INTEGER NOT NULL,
    score       REAL NOT NULL,
    failure_type TEXT,
    detail_json TEXT NOT NULL,
    PRIMARY KEY (run_id, test_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS ix_results_failure ON test_results(failure_type);
"""


@dataclass
class HistoricalRun:
    run_id: str
    agent_name: str
    started_at: str
    pass_rate: float
    average_score: float
    total: int
    passed: int
    failed: int


class HistoryStore:
    """Append-only store for past runs."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ---- public API ------------------------------------------------------

    def record(self, report) -> None:
        """Persist a finished `EvalReport`."""
        summary = report.to_dict()
        with self._connect() as conn, closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO runs
                (run_id, agent_name, started_at, finished_at, total, passed,
                 failed, pass_rate, average_score, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.run_id,
                    report.agent_name,
                    report.started_at.isoformat(),
                    report.finished_at.isoformat(),
                    report.total,
                    report.passed,
                    report.failed,
                    report.pass_rate,
                    report.average_score,
                    json.dumps(summary, default=str),
                ),
            )
            for r in report.results:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO test_results
                    (run_id, test_id, passed, score, failure_type, detail_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.run_id,
                        r.test_case.id,
                        int(r.passed),
                        r.score,
                        r.failure_report.failure_type if r.failure_report else None,
                        json.dumps(r.to_dict(), default=str),
                    ),
                )
            conn.commit()

    def history(
        self,
        *,
        agent_name: Optional[str] = None,
        limit: int = 50,
    ) -> list[HistoricalRun]:
        sql = (
            "SELECT run_id, agent_name, started_at, pass_rate, average_score, "
            "total, passed, failed FROM runs"
        )
        params: list[Any] = []
        if agent_name:
            sql += " WHERE agent_name = ?"
            params.append(agent_name)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        # Reverse so callers iterating chronologically see oldest -> newest.
        return [
            HistoricalRun(
                run_id=row[0],
                agent_name=row[1],
                started_at=row[2],
                pass_rate=row[3],
                average_score=row[4],
                total=row[5],
                passed=row[6],
                failed=row[7],
            )
            for row in reversed(rows)
        ]

    # ---- internals -------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
