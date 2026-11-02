"""Real SQLite enforcement, tenant isolation and deterministic synthetic seeding."""

import sqlite3
import subprocess
import sys
from contextlib import closing

import pytest

from app.agent.core_banking import CoreBanking
from app.contracts import User
from scripts.seed_core_banking import seed


@pytest.fixture
def bank(tmp_path):
    return CoreBanking(seed(tmp_path / "bank #? synthetic.db"))


@pytest.mark.parametrize("sql", [
    "INSERT INTO accounts VALUES ('new', 'user', 0, 'VND')",
    "UPDATE accounts SET balance = 0",
    "DELETE FROM transactions",
    "CREATE TABLE unexpected (id INTEGER)",
    "DROP TABLE accounts",
])
def test_connection_rejects_every_write(bank, sql):
    with closing(bank.connect()) as connection, pytest.raises(sqlite3.OperationalError, match="readonly database"):
        connection.execute(sql)


def test_queries_are_scoped_to_user_and_account(bank):
    user = User("synthetic-user-1", "public")
    assert [row["id"] for row in bank.accounts(user)] == ["SYN-ACC-001"]
    rows = bank.transactions(user)
    assert len(rows) == 5
    assert {row["account_id"] for row in rows} == {"SYN-ACC-001"}
    assert rows == bank.transactions(user, "SYN-ACC-001")
    assert bank.transactions(user, "SYN-ACC-002") == []
    assert bank.transactions(user, "missing") == []
    assert len(bank.transactions(user, limit=2)) == 2
    assert [row["ts"] for row in rows] == sorted((row["ts"] for row in rows), reverse=True)


@pytest.mark.parametrize("role", ["staff", "approver", "service"])
def test_no_role_bypasses_user_filter(bank, role):
    unknown = User("unknown", "credit", role)
    assert bank.accounts(unknown) == bank.transactions(unknown) == []


def test_sql_injection_is_only_a_bound_value(bank):
    attack = "' OR 1=1; DROP TABLE accounts; --"
    assert bank.accounts(User(attack, "public")) == []
    assert bank.transactions(User(attack, "public")) == []
    assert bank.transactions(User("synthetic-user-1", "public"), attack) == []
    assert len(bank.accounts(User("synthetic-user-1", "public"))) == 1


@pytest.mark.parametrize("limit", [0, -1, 101, True, "10", 1.5])
def test_invalid_limit(bank, limit):
    with pytest.raises(ValueError, match="limit"):
        bank.transactions(User("synthetic-user-1", "public"), limit=limit)


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        CoreBanking(path).accounts(User("user", "public"))
    assert not path.exists()


def test_seed_is_deterministic_and_refuses_overwrite(tmp_path):
    first, second = seed(tmp_path / "first.db"), seed(tmp_path / "second.db")
    with closing(sqlite3.connect(first)) as a, closing(sqlite3.connect(second)) as b:
        assert list(a.iterdump()) == list(b.iterdump())
        assert a.execute("SELECT count(*) FROM accounts").fetchone()[0] == 3
        assert a.execute("SELECT count(*) FROM transactions").fetchone()[0] == 15
        assert a.execute("PRAGMA foreign_key_check").fetchall() == []
    before = first.read_bytes()
    with pytest.raises(FileExistsError):
        seed(first)
    assert first.read_bytes() == before


def test_seed_cli(tmp_path):
    path = tmp_path / "cli.db"
    subprocess.run([sys.executable, "scripts/seed_core_banking.py", "--path", str(path)], check=True)
    assert len(CoreBanking(path).accounts(User("synthetic-user-1", "public"))) == 1


def test_default_path_from_environment(tmp_path, monkeypatch):
    path = seed(tmp_path / "configured.db")
    monkeypatch.setenv("CORE_BANKING_DB_PATH", str(path))
    assert CoreBanking().path == path
