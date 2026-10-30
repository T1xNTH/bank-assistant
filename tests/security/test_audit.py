import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.contracts import User
from app.deps import get_answerer, get_current_user
from app.fakes_runtime import CannedAnswerer
from app.main import create_app
from app.security import audit, pii
from app.security.auth import require_role


def rows():
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT * FROM audit_log ORDER BY rowid")]


def test_one_ask_row_contains_masked_question_and_result_metadata(monkeypatch):
    secret = "synthetic-private-input"
    masked = "[MASKED]"
    monkeypatch.setattr(pii, "mask_text", lambda text: (masked, ["TEST"]))
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: User("staff-1", "hr")

    class Answerer:
        def answer(self, *args):
            return replace(CannedAnswerer().answer(*args), route="local", trace_id="test-trace")

    app.dependency_overrides[get_answerer] = Answerer
    response = TestClient(app).post("/ask", json={"question": secret})
    assert response.status_code == 200
    [row] = rows()
    assert row["user_id"] == "staff-1" and row["department"] == "hr"
    assert row["endpoint"] == "/ask" and row["question_masked"] == masked
    assert row["route"] == "local" and row["refused"] == 0 and row["trace_id"] == "test-trace"
    assert row["latency_ms"] >= 0 and datetime.fromisoformat(row["ts"]).utcoffset().total_seconds() == 0
    assert row["cost_usd"] is None  # AskResult has no cost data: do not invent a value.
    assert secret not in json.dumps(row)


def test_refusal_is_audited_once_and_uses_request_id_when_trace_is_absent():
    response = TestClient(create_app()).post("/ask", json={"question": "ngoài phạm vi"})
    assert response.status_code == 200 and response.json()["found"] is False
    [row] = rows()
    assert row["refused"] == 1 and row["route"] == "cloud"
    assert row["trace_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize("mode", ["unimplemented", "error", "bad-output"])
def test_masker_failure_never_persists_raw_input(monkeypatch, mode):
    def mask(_):
        if mode == "unimplemented":
            raise NotImplementedError
        if mode == "error":
            raise RuntimeError("private diagnostic")
        return None, []

    monkeypatch.setattr(pii, "mask_text", mask)
    secret = "synthetic-private-question"
    assert TestClient(create_app()).post("/ask", json={"question": secret}).status_code == 200
    [row] = rows()
    assert row["question_masked"] == audit.REDACTED
    assert secret not in json.dumps(row)


def test_rejected_requests_and_health_each_create_one_row_without_raw_data(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    registry = tmp_path / "keys.json"
    registry.write_text("{}")
    monkeypatch.setenv("API_KEYS_FILE", str(registry))
    client = TestClient(create_app())
    responses = [
        client.get("/health"),
        client.post("/ask", json={"question": "private"}, headers={"X-API-Key": "bad-key"}),
        client.get("/private-customer?account=private"),
        client.post("/health"),
    ]
    assert [response.status_code for response in responses] == [200, 401, 404, 405]
    recorded = rows()
    assert len(recorded) == len(responses)
    assert [r["trace_id"] for r in recorded] == [r.headers["x-request-id"] for r in responses]
    assert all(r["question_masked"] is None and r["route"] is None and r["refused"] is None for r in recorded)
    assert "private" not in json.dumps(recorded) and "bad-key" not in json.dumps(recorded)


@pytest.mark.parametrize("body", [{}, {"question": "private", "top_k": 0}, b'{"question":"private"'])
def test_validation_failure_creates_one_row_without_capturing_the_body(body):
    client = TestClient(create_app())
    response = client.post("/ask", content=body) if isinstance(body, bytes) else client.post("/ask", json=body)
    assert response.status_code == 400
    [row] = rows()
    assert row["question_masked"] is None and row["route"] is None and row["refused"] is None
    assert "private" not in json.dumps(row)


def test_forbidden_request_records_authenticated_identity():
    app = create_app()
    approver = require_role("approver")

    @app.get("/approval")
    def approval(user: User = Depends(approver)):
        return {"user": user.user_id}

    assert TestClient(app).get("/approval").status_code == 403
    [row] = rows()
    assert row["user_id"] == "dev" and row["department"] == "public"
    assert row["endpoint"] == "/approval" and row["refused"] is None


@pytest.mark.parametrize(
    ("question", "masked", "raw_pii"),
    [
        ("+84900000001 100 VND", "<PHONE_NUMBER> 100 VND", "+84900000001"),
        ("CCCD: 001 204 012 345", "CCCD: <CCCD>", "001 204 012 345"),
        ("STK: 0011-0049-12345", "STK: <ACCOUNT_NUMBER>", "0011-0049-12345"),
        ("SĐT0912345678", "SĐT<PHONE_NUMBER>", "0912345678"),
    ],
)
def test_answerer_failure_creates_one_row_without_inventing_a_route(caplog, question, masked, raw_pii):
    app = create_app()

    class Broken:
        def answer(self, *args):
            raise RuntimeError("private-provider-detail")

    app.dependency_overrides[get_answerer] = Broken
    response = TestClient(app).post("/ask", json={"question": question})
    assert response.status_code == 500
    [row] = rows()
    assert row["question_masked"] == masked
    assert row["route"] is None and row["refused"] is None
    assert row["trace_id"] == response.headers["x-request-id"]
    assert "private-provider-detail" not in json.dumps(row) + response.text + caplog.text
    assert raw_pii not in json.dumps(row) + response.text + caplog.text


@pytest.mark.parametrize("broken_answerer", [False, True])
def test_audit_failure_returns_safe_503_without_retry_or_success(monkeypatch, caplog, broken_answerer):
    calls = []

    def broken(**fields):
        calls.append(fields)
        raise sqlite3.OperationalError("private-path-and-diagnostic")

    monkeypatch.setattr(audit, "write", broken)
    app = create_app()

    class BrokenAnswerer:
        def answer(self, *args):
            raise RuntimeError("private-answerer-error")

    app.dependency_overrides[get_answerer] = BrokenAnswerer
    client = TestClient(app)
    response = client.post("/ask", json={"question": "private"}) if broken_answerer else client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service Unavailable"}}
    assert len(calls) == 1 and calls[0]["trace_id"] == response.headers["x-request-id"]
    assert "private-path-and-diagnostic" not in response.text + caplog.text


def test_unwritable_database_path_fails_closed(monkeypatch, tmp_path):
    path = tmp_path / "not-a-directory"
    path.write_text("occupied")
    monkeypatch.setenv("AUDIT_DB_PATH", str(path / "audit.db"))
    assert TestClient(create_app()).get("/health").status_code == 503


def test_concurrent_requests_are_not_lost_duplicated_or_mixed(monkeypatch):
    monkeypatch.setattr(pii, "mask_text", lambda text: ("[MASKED]", []))
    with TestClient(create_app()) as client, ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda _: client.post("/ask", json={"question": "test"}), range(24)))
    recorded = rows()
    assert all(response.status_code == 200 for response in responses)
    assert len(recorded) == 24
    assert {r["trace_id"] for r in recorded} == {r.headers["x-request-id"] for r in responses}
    assert len({r["trace_id"] for r in recorded}) == 24
    assert all(UUID(r["trace_id"]).version == 4 for r in recorded)


def test_writer_appends_parameterized_values_without_modifying_earlier_rows(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "audit.db"
    monkeypatch.setenv("AUDIT_DB_PATH", str(path))
    fields = {"endpoint": "/ask", "latency_ms": 2, "question_masked": "masked '); DROP TABLE audit_log; --"}
    audit.write(**fields, trace_id="first")
    [original] = rows()
    audit.write(**fields, trace_id="second")
    first, second = rows()
    assert first == original and second["trace_id"] == "second"
    assert first["question_masked"] == fields["question_masked"]
    assert Path(path).is_file()


@pytest.mark.parametrize("scenario,status", [("success", 200), ("auth", 401), ("validation", 400), ("backend", 503)])
def test_chat_after_merge_is_audited_once_without_capturing_message(monkeypatch, scenario, status):
    from app.deps import get_llm
    from app.llm import LLMError
    from tests.fakes import FakeLLM

    secret = "synthetic-private-chat-message"
    app = create_app()
    app.dependency_overrides[get_llm] = lambda: FakeLLM(
        reply=json.dumps({"answer": "ok", "intent": "question", "needs_human": False})
    )
    if scenario == "auth":
        monkeypatch.setenv("AUTH_BACKEND", "apikey")
    if scenario == "backend":
        class BrokenLLM:
            def chat(self, *args, **kwargs):
                raise LLMError(secret)
        app.dependency_overrides[get_llm] = BrokenLLM
    body = {"message": 42} if scenario == "validation" else {"message": secret}
    response = TestClient(app).post("/chat", json=body)
    assert response.status_code == status
    [row] = rows()
    assert row["endpoint"] == "/chat"
    assert row["trace_id"] == response.headers["x-request-id"]
    assert all(row[field] is None for field in ("question_masked", "route", "refused", "cost_usd"))
    assert row["user_id"] == (None if scenario == "auth" else "dev")
    assert secret not in json.dumps(row)
