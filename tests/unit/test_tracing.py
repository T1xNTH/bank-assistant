"""Real SDK + in-memory OTEL export: assert sink contents, hierarchy and HTTP/RQ correlation."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import fakeredis
import pytest
from fastapi.testclient import TestClient
from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import deps, tracing
from app.contracts import AskResult, Citation, Hit, LLMResult, User
from app.main import create_app
from app.queue import jobs
from app.rag import retrieve as retrieval
from app.rag.answer import RagAnswerer
from app.security import pii
from app.security.masking import mask_identifier

PII = "0912345678"
USER = User("owner@example.com", "credit")


@pytest.fixture
def sink(monkeypatch):
    provider, exporter = TracerProvider(), InMemorySpanExporter()
    client = Langfuse(
        public_key="pk-lf-" + uuid4().hex, secret_key="sk-lf-test", tracer_provider=provider,
        span_exporter=exporter,
        should_export_span=lambda span: span.instrumentation_scope.name == "bank-assistant",
    )
    monkeypatch.setattr(tracing, "_runtime", lambda: (client, provider.get_tracer("bank-assistant")))

    def spans():
        client.flush()
        return exporter.get_finished_spans()

    yield spans
    provider.shutdown()


def contents(spans):
    return json.dumps([dict(span.attributes) | {"events": [str(e) for e in span.events]} for span in spans])


@pytest.mark.parametrize("missing", ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"])
def test_missing_key_is_noop_without_backend_initialization(monkeypatch, missing):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.delenv(missing)
    monkeypatch.setattr(tracing, "_backend", lambda *args: pytest.fail("must not initialize SDK"))
    with tracing.observation("/ask", root=True, input=PII) as trace:
        assert trace.trace_id is None
    tracing.flush()


def test_masked_fields_and_exception_without_raw_message_or_stack(sink):
    with pytest.raises(ValueError, match=PII), tracing.observation("/ask", root=True, input=PII) as trace:
        trace.update(output=json.dumps({"phone": PII}), metadata={PII: PII})
        raise ValueError("private " + PII)
    [span] = sink()
    assert PII not in contents([span]) and "<PHONE_NUMBER>" in contents([span])
    assert not span.events
    assert span.attributes["langfuse.observation.status_message"] == "Operation failed"


def test_unicode_escaped_pii_is_masked_even_outside_valid_json(sink):
    escaped = "".join(f"\\u{ord(char):04x}" for char in PII)
    with tracing.observation("/ask", root=True, input="Call " + escaped):
        pass
    raw = contents(sink())
    assert PII not in raw and escaped not in raw and "<PHONE_NUMBER>" in raw


def test_masking_failure_redacts_trace_fields(sink, monkeypatch):
    monkeypatch.setattr(pii, "mask_text", lambda text: (_ for _ in ()).throw(RuntimeError(PII)))
    with tracing.observation("/ask", root=True, input=PII) as trace:
        trace.update(output=PII)
    assert PII not in contents(sink())
    assert "REDACTED" in contents(sink())


def test_initialization_failure_does_not_change_answer(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setattr(tracing, "_backend", lambda *args: (_ for _ in ()).throw(RuntimeError(PII)))
    with TestClient(create_app()) as client:
        response = client.post("/ask", json={"question": "Fee?"})
    assert response.status_code == 200 and response.json()["trace_id"] is None


def test_ask_response_and_audit_use_real_exported_trace_id(sink, monkeypatch):
    hits = [Hit("doc", "source.pdf", 1, "Fee " + PII, .9, "public")]
    llm = SimpleNamespace(chat=lambda *a, **kw: LLMResult("Call " + PII + " [1].", "test"))
    answerer = RagAnswerer(lambda *a: hits, llm)
    application = create_app()
    application.dependency_overrides[deps.get_answerer] = lambda: answerer
    with TestClient(application) as client:
        response = client.post("/ask", json={"question": "Call " + PII})
    assert response.status_code == 200
    spans = sink()
    root = next(span for span in spans if span.name == "/ask")
    assert response.json()["trace_id"] == f"{root.context.trace_id:032x}"
    assert {span.name for span in spans} == {"/ask", "retrieve", "llm"}
    assert all(span.context.trace_id == root.context.trace_id for span in spans)
    assert all(span.parent.span_id == root.context.span_id for span in spans if span is not root)
    assert PII not in contents(spans) and USER.user_id not in contents(spans)
    import os
    import sqlite3

    with sqlite3.connect(os.environ["AUDIT_DB_PATH"]) as db:
        assert db.execute("SELECT trace_id FROM audit_log").fetchone()[0] == response.json()["trace_id"]


def test_chat_has_llm_child_and_no_pii(sink):
    application = create_app()
    application.dependency_overrides[deps.get_llm] = lambda: SimpleNamespace(chat=lambda *a, **kw: LLMResult(
        json.dumps({"answer": "Call " + PII, "intent": "question", "needs_human": False}), "test",
    ))
    with TestClient(application) as client:
        assert client.post("/chat", json={"message": "Call " + PII}).status_code == 200
    spans = sink()
    assert {s.name for s in spans} == {"/chat", "llm"}
    assert PII not in contents(spans)


def test_worker_wait_and_processing_have_real_timestamps_and_trace_id(sink, monkeypatch):
    connection = fakeredis.FakeRedis()
    enqueued = datetime.now(timezone.utc) - timedelta(seconds=2)
    monkeypatch.setattr(jobs, "get_current_job", lambda: SimpleNamespace(connection=connection, enqueued_at=enqueued))
    monkeypatch.setattr(jobs, "get_answerer", lambda: SimpleNamespace(answer=lambda *a, **kw: AskResult(
        "Call " + PII, True, [Citation(1, "doc", 1, .9)], "dense", "local", 1,
    )))
    result = jobs.execute_ask({"question": "Call " + PII}, {"user_id": "hashed", "department": "credit"})
    spans = sink()
    root = next(s for s in spans if s.name == "/ask/jobs")
    wait = next(s for s in spans if s.name == "queue_wait")
    processing = next(s for s in spans if s.name == "processing")
    assert wait.start_time == root.start_time == int(enqueued.timestamp() * 1_000_000_000)
    assert wait.end_time <= processing.start_time <= processing.end_time <= root.end_time
    assert wait.end_time - wait.start_time >= 2_000_000_000
    assert wait.parent.span_id == processing.parent.span_id == root.context.span_id
    assert result["trace_id"] == f"{root.context.trace_id:032x}"
    assert PII not in contents(spans) + json.dumps(result)
    connection.close()


def test_concurrent_traces_do_not_share_context(sink):
    def run(i):
        with tracing.observation("/ask", root=True, input=f"question {i}") as root:
            with tracing.observation("retrieve") as child:
                assert child.trace_id == root.trace_id
            return root.trace_id

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(run, range(8)))
    assert len(set(ids)) == 8 and len(sink()) == 16
    assert tracing._CURRENT.get() is None


def test_numeric_otel_trace_ids_are_preserved_for_response_and_polling():
    assert mask_identifier("01234567890123456789012345678901") == "01234567890123456789012345678901"
    assert PII not in mask_identifier(PII)


def test_real_retrieve_path_emits_rerank_child(sink, monkeypatch):
    # Keep the hybrid_rerank branch real; stub only embedding/storage/model dependencies.
    original = retrieval.retrieve
    hits = [Hit("doc", "source.pdf", 1, "content", .9, "public")]

    def dispatch(question, user, k, mode, **kwargs):
        return hits if mode == "hybrid" else original(question, user, k, mode, **kwargs)

    monkeypatch.setattr(retrieval, "retrieve", dispatch)
    monkeypatch.setattr(retrieval.rerank, "rerank", lambda *a: hits)
    with tracing.observation("/ask", root=True):
        assert original("Fee?", USER, 5, "hybrid_rerank") == hits
    assert {s.name for s in sink()} == {"/ask", "rerank"}


def test_flush_failure_does_not_change_result(sink, monkeypatch):
    client, _ = tracing._runtime()
    monkeypatch.setattr(client, "flush", lambda: (_ for _ in ()).throw(RuntimeError(PII)))
    tracing.flush()


def test_worker_error_exports_only_generic_failure(sink, monkeypatch):
    connection = fakeredis.FakeRedis()
    monkeypatch.setattr(jobs, "get_current_job", lambda: SimpleNamespace(
        connection=connection, enqueued_at=datetime.now(timezone.utc),
    ))
    monkeypatch.setattr(jobs, "get_answerer", lambda: (_ for _ in ()).throw(RuntimeError(PII)))
    with pytest.raises(RuntimeError, match="^Job execution failed$"):
        jobs.execute_ask({"question": "Call " + PII}, {"user_id": "hashed", "department": "credit"})
    spans = sink()
    assert PII not in contents(spans) and all(not s.events for s in spans)
    assert {s.name for s in spans} == {"/ask/jobs", "queue_wait", "processing"}
    connection.close()
