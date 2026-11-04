"""Append-only audit log in data/audit.db.

Owner: B — Epic E-006. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.security.masking import REDACTED as REDACTED
from app.security.masking import mask_identifier, mask_text


def write(
    *,
    user_id: str | None = None,
    department: str | None = None,
    endpoint: str,
    question_masked: str | None = None,
    route: str | None = None,
    refused: bool | None = None,
    latency_ms: int,
    cost_usd: float | None = None,
    trace_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """Commit one append-only row, defensively masking every text field.

    A separate connection/transaction per call supports sync workers and concurrent
    requests. SQLite serializes writers and waits up to 10 seconds for a lock.
    Unknown values stay NULL, rather than pretending a failed request cost zero.
    """
    path = Path(os.getenv("AUDIT_DB_PATH", "data/audit.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                ts TEXT NOT NULL, user_id TEXT, department TEXT, endpoint TEXT NOT NULL,
                question_masked TEXT, route TEXT, refused INTEGER CHECK (refused IN (0, 1)),
                latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
                cost_usd REAL, trace_id TEXT, input_tokens INTEGER, output_tokens INTEGER
            )"""
        )
        # Additive migration for existing installations. Serialize schema inspection and
        # ALTER together so concurrent writers cannot both try to add the same column.
        connection.execute("BEGIN IMMEDIATE")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(audit_log)")}
        for column in ("input_tokens", "output_tokens"):
            if column not in columns:
                connection.execute(f"ALTER TABLE audit_log ADD COLUMN {column} INTEGER")
        connection.execute(
            """INSERT INTO audit_log
                (ts, user_id, department, endpoint, question_masked, route, refused, latency_ms, cost_usd, trace_id,
                 input_tokens, output_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                *(mask_text(v) if v is not None else None for v in
                  (user_id, department, endpoint, question_masked, route)),
                refused, latency_ms, cost_usd, mask_identifier(trace_id) if trace_id is not None else None,
                input_tokens, output_tokens,
            ),
        )
