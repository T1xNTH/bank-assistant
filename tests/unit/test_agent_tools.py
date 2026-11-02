"""Real SQLite tool isolation, output masking and proposals without writes."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from app.agent.core_banking import CoreBanking
from app.agent.loan import tinh_lai_vay
from app.agent.tools import AgentTools, ToolUnavailable
from app.contracts import User
from app.security import pii
from app.security.masking import MaskingError
from scripts.seed_core_banking import seed


@pytest.fixture
def bank(tmp_path):
    path = seed(tmp_path / "bank.db")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "INSERT INTO accounts VALUES (?, ?, ?, ?)", ("1234567890123", "synthetic-user-1", 1000, "VND"),
        )
        connection.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", (
            "0901234567", "1234567890123", 1000,
            "CCCD 001204012345; phone 0912345678", "2026-02-01T00:00:00+00:00",
        ))
    return CoreBanking(path)


@pytest.mark.parametrize("role", ["staff", "approver", "service"])
def test_lookup_only_reads_current_user(bank, role):
    tools = AgentTools(User("synthetic-user-1", "credit", role), bank)
    assert len(tools.tra_cuu_giao_dich()) == 6
    assert tools.tra_cuu_giao_dich("SYN-ACC-002") == []
    assert tools.tra_cuu_giao_dich("' OR 1=1 --") == []
    assert len(tools.tra_cuu_giao_dich("SYN-ACC-001", limit=2)) == 2
    assert AgentTools(User("unknown", "credit", role), bank).tra_cuu_giao_dich() == []


def test_every_transaction_string_is_masked(bank):
    rows = AgentTools(User("synthetic-user-1", "credit"), bank).tra_cuu_giao_dich("1234567890123")
    encoded = json.dumps(rows)
    assert len(rows) == 1 and rows[0]["amount"] == 1000
    for raw in ("1234567890123", "0901234567", "001204012345", "0912345678"):
        assert raw not in encoded
    assert "<PHONE_NUMBER>" in encoded and "<CCCD>" in encoded
    with closing(bank.connect()) as connection:
        assert "0912345678" in connection.execute(
            "SELECT description FROM transactions WHERE id = ?", ("0901234567",),
        ).fetchone()[0]  # Output masking does not mutate the source.


def test_user_identity_cannot_be_supplied_as_tool_argument(bank):
    tools = AgentTools(User("synthetic-user-1", "credit"), bank)
    for method in (tools.tra_cuu_giao_dich, tools.tao_ticket):
        with pytest.raises(TypeError):
            method(user_id="synthetic-user-2")


def test_bound_users_do_not_cross_between_concurrent_calls(bank):
    tools = [AgentTools(User(f"synthetic-user-{i}", "credit"), bank) for i in (2, 3)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda tool: tool.tra_cuu_giao_dich(), tools))
    for i, rows in zip((2, 3), results, strict=True):
        assert {row["account_id"] for row in rows} == {f"SYN-ACC-{i:03d}"}


def test_pending_proposal_never_opens_database(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Ticket proposal must not open SQLite")

    monkeypatch.setattr(sqlite3, "connect", unexpected)
    monkeypatch.setenv("TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    result = AgentTools(User("synthetic-user-1", "credit")).tao_ticket("Investigate CCCD 001204012345")
    assert result == {
        "status": "pending", "created_by": "synthetic-user-1", "summary": "Investigate CCCD <CCCD>",
    }
    assert list(tmp_path.iterdir()) == []


def test_approver_tool_still_only_proposes_and_masks_owner():
    proposal = AgentTools(User("0912345678", "credit", "approver")).tao_ticket("Check transfer")
    assert proposal["status"] == "pending" and "0912345678" not in json.dumps(proposal)
    assert "approved_by" not in proposal


@pytest.mark.parametrize("summary", ["", " ", "x" * 2001, None, 123])
def test_invalid_ticket_summary(summary):
    with pytest.raises(ValueError):
        AgentTools(User("user", "credit")).tao_ticket(summary)


@pytest.mark.parametrize("account_id", ["", " ", "a" * 129, 1])
def test_invalid_account_filter(bank, account_id):
    with pytest.raises(ValueError):
        AgentTools(User("synthetic-user-1", "credit"), bank).tra_cuu_giao_dich(account_id)


def test_masking_failure_never_returns_raw_data(bank, monkeypatch):
    def unavailable(text):
        raise RuntimeError("0912345678")

    monkeypatch.setattr(pii, "mask_text", unavailable)
    tools = AgentTools(User("synthetic-user-1", "credit"), bank)
    for action in (tools.tra_cuu_giao_dich, lambda: tools.tao_ticket("0912345678")):
        with pytest.raises(MaskingError) as error:
            action()
        assert "0912345678" not in str(error.value)


def test_missing_bank_is_sanitized_and_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(ToolUnavailable, match="^Transaction lookup unavailable$"):
        AgentTools(User("user", "credit"), CoreBanking(path)).tra_cuu_giao_dich()
    assert not path.exists()


def test_loan_tool_delegates_to_validated_calculator():
    tools = AgentTools(User("user", "credit"))
    assert tools.tinh_lai_vay(1000, 12, 2) == tinh_lai_vay(1000, 12, 2)
    with pytest.raises(ValueError):
        tools.tinh_lai_vay(-1, 12, 2)
