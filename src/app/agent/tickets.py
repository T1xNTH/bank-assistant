"""Ticket store; writes only after approver decision.

Owner: B — Epic E-011. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.contracts import User


@dataclass(frozen=True)
class TicketDecision:
    """Trusted approval-layer input, never deserialized from model/tool arguments.

    The graph/endpoint must authenticate approver and resolve its pending proposal
    before constructing this value. Pending proposals alone cannot write tickets.
    Thread ownership, decision persistence and replay prevention belong to T-030/31.
    """

    created_by: str
    summary: str
    approver: User
    approved: bool


class TicketStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path if path is not None else os.getenv("TICKETS_DB_PATH", "data/tickets.db"))

    def create(
        self, created_by: str, summary: str, approved_by: str, *, decision: TicketDecision | None = None,
    ) -> dict:
        """Persist only an explicitly approved, matching proposal; return its row.

        approved_by alone is insufficient. Validate before opening/creating a DB.
        No arbitrary SQL or write connection is exposed to the agent tool layer.
        """
        if (
            not isinstance(decision, TicketDecision)
            or decision.approved is not True
            or not isinstance(decision.approver, User)
            or decision.approver.role != "approver"
            or decision.approver.user_id != approved_by
            or decision.created_by != created_by
            or decision.summary != summary
        ):
            raise PermissionError("A matching approver decision is required")
        if any(not isinstance(value, str) or not value.strip() for value in (created_by, summary, approved_by)):
            raise ValueError("created_by, summary and approved_by must be non-empty strings")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY,
                    created_by TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    ts TEXT NOT NULL
                )"""
            )
            cursor = connection.execute(
                "INSERT INTO tickets (created_by, summary, status, approved_by, ts) VALUES (?, ?, ?, ?, ?)",
                (created_by, summary, "open", approved_by, datetime.now(timezone.utc).isoformat()),
            )
            return dict(connection.execute("SELECT * FROM tickets WHERE id = ?", (cursor.lastrowid,)).fetchone())

