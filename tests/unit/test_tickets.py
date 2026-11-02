"""Ticket writes require trusted approval bound to the exact proposal."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime

import pytest

from app.agent.tickets import TicketDecision, TicketStore
from app.contracts import User


@pytest.fixture
def decision():
    return TicketDecision(
        "synthetic-user-1", "Investigate synthetic transfer", User("reviewer", "credit", "approver"), True,
    )


def create(store, decision):
    return store.create(decision.created_by, decision.summary, decision.approver.user_id, decision=decision)


def test_ticket_schema_and_durable_approved_row(tmp_path, decision):
    path = tmp_path / "nested" / "tickets.db"
    row = create(TicketStore(path), decision)
    assert row == {
        "id": 1, "created_by": decision.created_by, "summary": decision.summary,
        "status": "open", "approved_by": "reviewer", "ts": row["ts"],
    }
    assert datetime.fromisoformat(row["ts"]).utcoffset().total_seconds() == 0
    with closing(sqlite3.connect(path)) as connection:
        assert [col[1] for col in connection.execute("PRAGMA table_info(tickets)")] == [
            "id", "created_by", "summary", "status", "approved_by", "ts",
        ]
        assert connection.execute("SELECT * FROM tickets").fetchall() == [tuple(row.values())]


@pytest.mark.parametrize("kind", [
    "missing", "reject", "staff", "service", "other-user", "other-summary", "other-approver", "dict",
])
def test_invalid_decision_does_not_even_create_database(tmp_path, decision, kind):
    path = tmp_path / "uncreated" / "tickets.db"
    supplied = decision
    if kind == "missing":
        supplied = None
    elif kind == "reject":
        supplied = replace(decision, approved=False)
    elif kind in {"staff", "service"}:
        supplied = replace(decision, approver=replace(decision.approver, role=kind))
    elif kind == "other-user":
        supplied = replace(decision, created_by="another-user")
    elif kind == "other-summary":
        supplied = replace(decision, summary="Changed after approval")
    elif kind == "other-approver":
        supplied = replace(decision, approver=replace(decision.approver, user_id="another-reviewer"))
    elif kind == "dict":
        supplied = {"approved": True, "approved_by": "reviewer"}
    with pytest.raises(PermissionError):
        TicketStore(path).create(decision.created_by, decision.summary, "reviewer", decision=supplied)
    assert not path.parent.exists()


def test_rejected_write_preserves_existing_rows(tmp_path, decision):
    path = tmp_path / "tickets.db"
    store = TicketStore(path)
    create(store, decision)
    before = path.read_bytes()
    with pytest.raises(PermissionError):
        create(store, replace(decision, approved=False))
    assert path.read_bytes() == before


def test_ticket_text_is_parameterized(tmp_path, decision):
    attack = "'); DROP TABLE tickets; --"
    approved = replace(decision, created_by=attack, summary=attack, approver=replace(decision.approver, user_id=attack))
    store = TicketStore(tmp_path / "tickets.db")
    row = create(store, approved)
    assert row["summary"] == row["created_by"] == row["approved_by"] == attack
    assert create(store, decision)["id"] == 2


@pytest.mark.parametrize("field", ["created_by", "summary"])
def test_empty_approved_values_rejected(tmp_path, decision, field):
    with pytest.raises(ValueError):
        create(TicketStore(tmp_path / "tickets.db"), replace(decision, **{field: " "}))
    assert not (tmp_path / "tickets.db").exists()


def test_concurrent_approved_writes_are_durable(tmp_path, decision):
    path = tmp_path / "tickets.db"
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(lambda _: create(TicketStore(path), decision), range(12)))
    assert len({row["id"] for row in rows}) == 12
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT count(*) FROM tickets").fetchone()[0] == 12


def test_environment_path(tmp_path, monkeypatch, decision):
    path = tmp_path / "configured.db"
    monkeypatch.setenv("TICKETS_DB_PATH", str(path))
    assert create(TicketStore(), decision)["id"] == 1
    assert path.exists()
