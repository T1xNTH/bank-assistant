"""Token and cost propagation across real HTTP/worker boundaries and existing SQLite."""

import json
import os
import sqlite3
from types import SimpleNamespace

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import deps, tracing
from app.contracts import Hit, LLMResult
from app.main import create_app
from app.queue import jobs
from app.rag.answer import RagAnswerer
from app.security import audit


def row():
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute("SELECT * FROM audit_log ORDER BY rowid DESC LIMIT 1").fetchone())


def install(application, model):
    llm = SimpleNamespace(chat=lambda *a, **kw: LLMResult("Answer [1].", model, 100, 50))
    answerer = RagAnswerer(lambda *a: [Hit("doc", "file.pdf", 1, "fee", .9, "public")], llm)
    application.dependency_overrides[deps.get_answerer] = lambda: answerer
    return answerer


@pytest.mark.parametrize("model,expected", [("gpt-6-luna", .000035), ("unknown", None), ("qwen2.5:3b", 0.0)])
def test_ask_accounting_without_langfuse(model, expected, monkeypatch):
    monkeypatch.setattr(tracing, "_runtime", lambda: None)
    application = create_app()
    install(application, model)
    client = TestClient(application)
    assert client.post("/ask", json={"question": "fee?"}).status_code == 200
    result = row()
    assert (result["input_tokens"], result["output_tokens"], result["cost_usd"]) == (100, 50, expected)
    # New request must never inherit another request's usage.
    assert client.get("/health").status_code == 200
    assert row()["cost_usd"] is None and row()["input_tokens"] == 0


@pytest.mark.parametrize("valid", [True, False])
def test_chat_retains_billed_usage_even_when_output_is_invalid(valid):
    application = create_app()
    text = json.dumps({"answer": "OK", "intent": "other", "needs_human": False}) if valid else "bad json"
    llm = SimpleNamespace(chat=lambda *a, **kw: LLMResult(text, "gpt-6-luna", 100, 50))
    application.dependency_overrides[deps.get_llm] = lambda: llm
    response = TestClient(application).post("/chat", json={"message": "Hello"})
    assert response.status_code == (200 if valid else 503)
    assert row()["cost_usd"] == .000035


def test_worker_writes_processing_usage_and_masked_question(monkeypatch):
    application = create_app()
    answerer = install(application, "gpt-6-luna")
    connection = fakeredis.FakeRedis()
    monkeypatch.setattr(jobs, "get_current_job", lambda: SimpleNamespace(connection=connection, enqueued_at=None))
    monkeypatch.setattr(jobs, "get_answerer", lambda: answerer)
    try:
        jobs.execute_ask({"question": "Gọi 0912345678"}, {"user_id": "hashed", "department": "public"})
        result = row()
        assert result["endpoint"] == "/ask/jobs" and result["input_tokens"] == 100
        assert result["cost_usd"] == .000035 and "0912345678" not in result["question_masked"]
    finally:
        connection.close()


def test_existing_audit_database_is_migrated_without_changing_old_rows():
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        connection.execute("""CREATE TABLE audit_log (
            ts TEXT, user_id TEXT, department TEXT, endpoint TEXT, question_masked TEXT,
            route TEXT, refused INTEGER, latency_ms INTEGER, cost_usd REAL, trace_id TEXT)""")
        connection.execute("INSERT INTO audit_log (endpoint, cost_usd) VALUES ('old', 1.0)")
    audit.write(endpoint="/ask", latency_ms=1, input_tokens=100, output_tokens=50, cost_usd=.000035)
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        rows = connection.execute("SELECT endpoint, cost_usd, input_tokens FROM audit_log ORDER BY rowid").fetchall()
        assert rows == [
            ("old", 1.0, None), ("/ask", .000035, 100),
        ]
