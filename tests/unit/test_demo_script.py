"""Ordered T-043 demo rehearsal: real UI/API/auth/graph/SQLite, controlled hits and model."""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app import deps
from app.contracts import Hit, LLMResult
from app.main import create_app
from app.rag.answer import RagAnswerer
from scripts.seed_core_banking import seed

UI = Path(__file__).resolve().parents[2] / "ui"
sys.path.append(str(UI))
import ui_api  # noqa: E402

CREDIT = "Nhân viên tín dụng (credit, staff)"
HR = "Nhân viên nhân sự (hr, staff)"
APPROVER = "Người duyệt (approver)"
PHONE = "0912345678"  # synthetic canary; must not reach model/checkpoint/ticket
KEYPASS = "Phí cung ứng thiết bị xác thực Keypass cho khách hàng tổ chức dùng eFAST là bao nhiêu?"
WAGE = "Mức lương tối thiểu tháng vùng I là bao nhiêu?"
LOAN = "Vay 100 triệu, lãi 12%/năm, 12 tháng trả góp đều thì mỗi tháng trả bao nhiêu?"
# The demo's out-of-scope question, taken from eval/golden.jsonl (in_scope: false).
OUT_OF_SCOPE = "Giá vàng SJC hôm nay mua vào bán ra bao nhiêu?"


class DemoModel:
    def __init__(self):
        self.calls = []
        self.replies = iter([
            "Phí Keypass là 330.000 đồng/thiết bị, chưa gồm VAT. [1]",
            "Mức lương tối thiểu tháng vùng I là 5.310.000 đồng. [1]",
            "Phí Keypass là 330.000 đồng/thiết bị, chưa gồm VAT. [1]",
            json.dumps({"tool": "tinh_lai_vay", "args": {
                "principal": 100000000, "annual_rate_percent": 12, "months": 12,
            }}),
            json.dumps({"tool": "tao_ticket", "args": {"summary": "Kiểm tra phí, liên hệ " + PHONE}}),
        ])

    def chat(self, messages, alias, temperature=0.0):
        self.calls.append((messages, alias))
        return LLMResult(next(self.replies), "scripted/demo")


def demo_hits(question, user, k, mode):
    """Controlled hit fixture, not a replacement for actual Qdrant/RBAC corpus tests."""
    if "lương" in question.casefold():
        if user.department != "hr":
            return []
        return [Hit("wage", "293-cp.signed.pdf", 2, "Vùng I: 5.310.000 đồng", 0.9, "hr")]
    if "keypass" in question.casefold():
        return [Hit("fee", "dichvunhdt.pdf", 7, "Keypass: 330.000 đồng/thiết bị, chưa gồm VAT", 0.9, "public")]
    return []


def test_five_minute_demo_sequence(monkeypatch, tmp_path):
    identities = {
        "demo-credit-key": ("synthetic-user-1", "credit", "staff"),
        "demo-hr-key": ("synthetic-user-2", "hr", "staff"),
        "demo-approver-key": ("demo-approver", "credit", "approver"),
    }
    registry = tmp_path / "keys.json"
    registry.write_text(json.dumps({
        hashlib.sha256(key.encode()).hexdigest(): {"user_id": user, "department": department, "role": role}
        for key, (user, department, role) in identities.items()
    }))
    for key, value in {
        "AUTH_BACKEND": "apikey", "API_KEYS_FILE": str(registry),
        "CORE_BANKING_DB_PATH": str(seed(tmp_path / "bank.db")),
        "TICKETS_DB_PATH": str(tmp_path / "tickets.db"),
        "AGENT_CHECKPOINT_DB_PATH": str(tmp_path / "checkpoints.db"),
        "UI_KEY_CREDIT_STAFF": "demo-credit-key", "UI_KEY_HR_STAFF": "demo-hr-key",
        "UI_KEY_APPROVER": "demo-approver-key",
    }.items():
        monkeypatch.setenv(key, value)
    model = DemoModel()
    app = create_app()
    app.dependency_overrides[deps.get_llm] = lambda: model
    app.dependency_overrides[deps.get_answerer] = lambda: RagAnswerer(demo_hits, model)

    with TestClient(app) as client:
        def forward(request):
            response = client.request(request.method, request.url.raw_path.decode(), content=request.content,
                                      headers={k: v for k, v in request.headers.items()
                                               if k.lower() in ("x-api-key", "content-type")})
            return httpx.Response(response.status_code, headers=response.headers, content=response.content)

        monkeypatch.setattr(ui_api, "TRANSPORT", httpx.MockTransport(forward))
        at = AppTest.from_file(str(UI / "app.py"), default_timeout=30).run()

        def ask(question):
            at.text_area[0].set_value(question)
            at.button(key="FormSubmitter:ask-Hỏi").click()
            at.run()
            assert not at.exception
            return at.session_state["ask_history"][at.sidebar.radio(key="role").value][-1]["result"]

        fee = ask(KEYPASS)
        assert fee["found"] and fee["route"] == "cloud"
        assert [(c["source"], c["page"]) for c in fee["citations"]] == [("dichvunhdt.pdf", 7)]
        assert not ask(WAGE)["citations"]  # no HR context for the credit user in this controlled fixture
        at.sidebar.radio(key="role").set_value(HR)
        at.run()
        assert ask(WAGE)["citations"][0]["source"] == "293-cp.signed.pdf"
        at.sidebar.radio(key="role").set_value(CREDIT)
        at.run()
        assert ask(f"Liên hệ {PHONE}. Phí cung ứng thiết bị xác thực Keypass là bao nhiêu?")["route"] == "local"

        at.text_area[1].set_value(LOAN)
        at.button(key="FormSubmitter:agent-Gửi").click()
        at.run()
        assert not at.exception
        [thread_id] = at.session_state["threads"].keys()
        assert "8.884.878,87" in at.session_state["threads"][thread_id]["messages"][-1][1]

        at.text_area[1].set_value(f"Tạo ticket kiểm tra phí, liên hệ {PHONE}")
        at.button(key="FormSubmitter:agent-Gửi").click()
        at.run()
        thread = at.session_state["threads"][thread_id]
        assert thread["status"] == "pending_approval" and PHONE not in json.dumps(thread["pending"])
        assert not (tmp_path / "tickets.db").exists()
        at.sidebar.radio(key="role").set_value(APPROVER)
        at.run()
        at.button(key=f"approve-{thread_id}").click()
        at.run()
        assert not at.exception and at.session_state["decided"]["status"] == "completed"
        with sqlite3.connect(tmp_path / "tickets.db") as connection:
            [(ticket_id, owner, approver, summary)] = connection.execute(
                "SELECT id, created_by, approved_by, summary FROM tickets",
            ).fetchall()
        assert owner == "synthetic-user-1" and approver == "demo-approver" and PHONE not in summary
        assert str(ticket_id) in at.session_state["decided"]["answer"]

        at.text_input(key="manual-thread").set_value(thread_id)
        at.button(key="manual-approve").click()
        at.run()
        assert not at.exception and any("HTTP 409" in error.value for error in at.error)
        with sqlite3.connect(tmp_path / "tickets.db") as connection:
            assert connection.execute("SELECT count(*) FROM tickets").fetchone()[0] == 1
        at.sidebar.radio(key="role").set_value(CREDIT)
        at.run()
        refusal = ask(OUT_OF_SCOPE)
        assert not refusal["found"] and not refusal["citations"]
        assert [alias for _, alias in model.calls] == [
            "cloud-chat", "cloud-chat", "local-chat", "cloud-chat", "local-chat",
        ]
        assert all(PHONE not in json.dumps(messages) for messages, _ in model.calls)


def test_demo_out_of_scope_question_is_an_out_of_scope_golden_row():
    rows = [json.loads(line) for line in (UI.parent / "eval/golden.jsonl").read_text(encoding="utf-8").splitlines()]
    [row] = [r for r in rows if r["user_input"] == OUT_OF_SCOPE]
    assert row["in_scope"] is False
    assert OUT_OF_SCOPE in (UI.parent / "docs/00-project/demo-script.md").read_text(encoding="utf-8")
