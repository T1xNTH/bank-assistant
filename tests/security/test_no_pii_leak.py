"""Scan actual output, captured logs and SQLite bytes for synthetic PII."""

import io
import json
import logging
import os
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.contracts import Citation
from app.deps import get_answerer, get_llm
from app.fakes_runtime import CannedAnswerer
from app.log_config import JsonFormatter
from app.main import create_app
from app.security import audit, pii
from tests.fakes import FakeLLM

CCCD = "001204012345"
PHONE = "0912345678"
ACCOUNT = "1903678901234"
RAW = f"CCCD: {CCCD}; SDT: {PHONE}; STK: {ACCOUNT}"


def assert_clean(value):
    for secret in (CCCD, PHONE, ACCOUNT):
        assert secret not in value


@pytest.mark.parametrize("endpoint", ["/ask", "/chat"])
@pytest.mark.parametrize("failure", [False, True])
def test_request_output_logs_and_audit_are_masked(endpoint, failure, caplog):
    app = create_app()
    calls = []

    class Answerer:
        def answer(self, question, user, mode):
            calls.append(question)
            logging.getLogger("app.boundary").info("received %s", question)
            if failure:
                raise RuntimeError(RAW)
            return replace(
                CannedAnswerer().answer(question, user, mode), answer=RAW,
                citations=[Citation(1, RAW, 1, 1.0)], trace_id=CCCD,
            )

    class ChatLLM:
        def chat(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            logging.getLogger("app.boundary").info("received %s", calls[-1])
            if failure:
                raise RuntimeError(RAW)
            return FakeLLM(reply=json.dumps({
                "answer": RAW, "intent": "question", "needs_human": False,
            })).chat(messages, **kwargs)

    app.dependency_overrides[get_answerer] = Answerer
    app.dependency_overrides[get_llm] = ChatLLM
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post(endpoint, json={"question" if endpoint == "/ask" else "message": RAW})
    assert response.status_code == (500 if failure else 200)
    assert calls and "<CCCD>" in calls[0]
    assert_clean(json.dumps(calls) + response.text + caplog.text)
    assert_clean("\n".join(JsonFormatter().format(record) for record in caplog.records))
    path = Path(os.environ["AUDIT_DB_PATH"])
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT * FROM audit_log").fetchall()
    assert len(rows) == 1
    assert_clean(repr(rows))
    for file in path.parent.glob("audit.db*"):
        assert_clean(file.read_bytes().decode("latin1"))


def test_logging_masks_interpolation_extras_exception_and_stack(caplog):
    create_app()
    stream = io.StringIO()
    handler = next(h for h in logging.getLogger().handlers if h.name == "bank-assistant-json")
    previous = handler.setStream(stream)
    try:
        try:
            raise ValueError(RAW)
        except ValueError:
            logging.getLogger("app.boundary").exception(
                "customer %s", RAW, extra={"route": RAW, "customer": {"details": RAW}}, stack_info=True,
            )
    finally:
        handler.setStream(previous)
    assert_clean(stream.getvalue() + caplog.text + repr([vars(r) for r in caplog.records]))
    assert json.loads(stream.getvalue())["exception_type"] == "ValueError"


def test_audit_writer_defends_against_unmasked_callers():
    audit.write(
        user_id=RAW, department=RAW, endpoint=RAW, question_masked=RAW,
        route=RAW, trace_id=RAW, latency_ms=1,
    )
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        assert_clean(repr(connection.execute("SELECT * FROM audit_log").fetchall()))
    assert_clean(Path(os.environ["AUDIT_DB_PATH"]).read_bytes().decode("latin1"))


@pytest.mark.parametrize("invalid", [False, True])
@pytest.mark.parametrize("endpoint", ["/ask", "/chat"])
def test_masker_failure_never_passes_raw_input_to_backend(monkeypatch, invalid, endpoint, caplog):
    def broken(text):
        if invalid:
            return None, []
        raise RuntimeError(RAW)

    monkeypatch.setattr(pii, "mask_text", broken)
    app = create_app()
    calls = []

    class Answerer:
        def answer(self, question, user, mode):
            calls.append(question)
            return CannedAnswerer().answer(question, user, mode)

    class ChatLLM:
        def chat(self, messages, **kwargs):
            calls.append(messages[-1]["content"])
            return FakeLLM(reply=json.dumps({
                "answer": RAW, "intent": "question", "needs_human": False,
            })).chat(messages, **kwargs)

    app.dependency_overrides[get_answerer] = Answerer
    app.dependency_overrides[get_llm] = ChatLLM
    response = TestClient(app).post(endpoint, json={"question" if endpoint == "/ask" else "message": RAW})
    assert response.status_code == 200
    assert calls == [audit.REDACTED]
    assert_clean(response.text + caplog.text)
    assert_clean(Path(os.environ["AUDIT_DB_PATH"]).read_bytes().decode("latin1"))


def test_uuid_trace_matches_response_audit_and_logs(caplog):
    trace = "d53895ab-7422-4102-a53a-8eed049fcfbd"
    app = create_app()

    class Answerer:
        def answer(self, *args):
            return replace(CannedAnswerer().answer(*args), trace_id=trace)

    app.dependency_overrides[get_answerer] = Answerer
    response = TestClient(app).post("/ask", json={"question": "hello"})
    assert response.json()["trace_id"] == trace
    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as connection:
        assert connection.execute("SELECT trace_id FROM audit_log").fetchone() == (trace,)


@pytest.mark.parametrize("body", [{"question": RAW, "top_k": 0}, {"message": RAW * 200}])
def test_invalid_requests_do_not_leak(body, caplog):
    response = TestClient(create_app()).post("/ask" if "question" in body else "/chat", json=body)
    assert response.status_code == 400
    assert_clean(response.text + caplog.text)
    assert_clean(Path(os.environ["AUDIT_DB_PATH"]).read_bytes().decode("latin1"))
