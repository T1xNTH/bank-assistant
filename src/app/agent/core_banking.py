"""Read-only SQLite access (mode=ro) to synthetic core banking data.

Owner: B — Epic E-011. See docs/00-project/product-plan.md.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app.contracts import User


class CoreBanking:
    """Read synthetic data for the authenticated user supplied by the caller.

    Never take the user identity from model/tool arguments. Each query opens and
    closes its own read-only connection; missing databases fail without creation.
    Amounts are integer VND. Results are newest first, bounded to 100 rows.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path if path is not None else os.getenv("CORE_BANKING_DB_PATH", "data/core_banking.db"))

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def accounts(self, user: User) -> list[dict]:
        with closing(self.connect()) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT id, user_id, balance, currency FROM accounts WHERE user_id = ? ORDER BY id",
                (user.user_id,),
            )]

    def transactions(self, user: User, account_id: str | None = None, *, limit: int = 20) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100")
        with closing(self.connect()) as connection:
            return [dict(row) for row in connection.execute(
                """SELECT t.id, t.account_id, t.amount, t.description, t.ts
                   FROM transactions AS t JOIN accounts AS a ON a.id = t.account_id
                   WHERE a.user_id = ? AND (? IS NULL OR a.id = ?)
                   ORDER BY t.ts DESC, t.id DESC LIMIT ?""",
                (user.user_id, account_id, account_id, limit),
            )]

