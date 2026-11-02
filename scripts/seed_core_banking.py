"""Create deterministic synthetic banking data. Refuse to overwrite existing files."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def _populate(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """CREATE TABLE accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                balance INTEGER NOT NULL,
                currency TEXT NOT NULL CHECK (currency = 'VND')
            )"""
        )
        connection.execute("CREATE INDEX accounts_user_id ON accounts(user_id)")
        connection.execute(
            """CREATE TABLE transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL REFERENCES accounts(id),
                amount INTEGER NOT NULL,
                description TEXT NOT NULL,
                ts TEXT NOT NULL
            )"""
        )
        connection.execute("CREATE INDEX transactions_account_ts ON transactions(account_id, ts)")
        accounts = [
            (f"SYN-ACC-{i:03d}", f"synthetic-user-{i}", i * 1_000_000, "VND")
            for i in range(1, 4)
        ]
        connection.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?)", accounts)
        connection.executemany(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?)",
            [
                (f"SYN-TXN-{i:03d}-{j:02d}", account_id, (-1) ** j * j * 10_000,
                 f"Synthetic transaction {j}", f"2026-01-{j:02d}T00:00:00+00:00")
                for i, (account_id, _, _, _) in enumerate(accounts, 1) for j in range(1, 6)
            ],
        )


def seed(path: str | Path = "data/core_banking.db") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Build and commit off-path. Publish only a complete database, without ever
    # replacing an existing destination (including one created concurrently).
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".core-banking-", suffix=".db", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        _populate(temporary)
        os.link(temporary, path)
    finally:
        temporary.unlink()
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("data/core_banking.db"))
    args = parser.parse_args()
    seed(args.path)
    print("Synthetic core banking database created")
