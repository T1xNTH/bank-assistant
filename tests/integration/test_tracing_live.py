"""Opt-in local Langfuse ingestion smoke with synthetic data and scripted RAG/model dependencies."""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app import deps, tracing
from app.contracts import LLMResult
from app.main import create_app
from app.queue import jobs
from app.rag import embed, rerank, retrieve
from app.rag.answer import RagAnswerer
from app.rag.store import upsert_chunks

pytestmark = [pytest.mark.integration, pytest.mark.filterwarnings("ignore:Payload indexes have no effect")]


def test_local_langfuse_ingests_masked_request_and_worker_spans(monkeypatch, tmp_path):
    if os.getenv("TRACING_LIVE_TEST") != "1":
        pytest.skip("Set TRACING_LIVE_TEST=1 and local LANGFUSE keys/base URL")
    assert os.environ["LANGFUSE_PUBLIC_KEY"] and os.environ["LANGFUSE_SECRET_KEY"]
    monkeypatch.setenv("RAG_BACKEND", "fake")  # Do not download models during the smoke.
    monkeypatch.setenv("AUTH_BACKEND", "fake")
    monkeypatch.setenv("WORKER_RPM", "60000")
    vector = [1.0] + [0.0] * (embed.DIM - 1)
    sparse = {"indices": [7], "values": [1.0]}
    monkeypatch.setattr(embed, "embed", lambda texts: ([vector] * len(texts), [sparse] * len(texts)))
    monkeypatch.setattr(rerank, "_model", lambda: SimpleNamespace(score=lambda pairs: [.9] * len(pairs)))
    qdrant = QdrantClient(":memory:")
    upsert_chunks([{
        "doc_id": "synthetic-policy", "source": "synthetic-policy.pdf", "page": 1, "chunk_index": 0,
        "text": "Synthetic internal fee policy.", "department": "public", "classification": "public",
        "effective_date": "2026-01-01", "superseded_by": None, "dense": vector, "sparse": sparse,
    }], client=qdrant, collection="obs_smoke")
    model = SimpleNamespace(chat=lambda *a, **kw: LLMResult("Synthetic policy [1].", "scripted"))
    answerer = RagAnswerer(
        lambda q, u, k, m: retrieve.retrieve(q, u, k, m, client=qdrant, collection="obs_smoke"), model,
    )
    app = create_app()
    app.dependency_overrides[deps.get_answerer] = lambda: answerer
    pii = "0912345678"
    ids = []
    with TestClient(app) as client:
        for _ in range(20):
            response = client.post("/ask", json={"question": "Synthetic policy, call " + pii})
            assert response.status_code == 200 and pii not in response.text
            ids.append(response.json()["trace_id"])
        assert client.post("/chat", json={"message": "Synthetic greeting"}).status_code == 200
    connection = fakeredis.FakeRedis()
    monkeypatch.setattr(jobs, "get_answerer", lambda: answerer)
    for delay in (.5, 1.0):
        monkeypatch.setattr(jobs, "get_current_job", lambda delay=delay: SimpleNamespace(
            connection=connection, enqueued_at=datetime.now(timezone.utc) - timedelta(seconds=delay),
        ))
        result = jobs.execute_ask({"question": "Synthetic policy, call " + pii}, {
            "user_id": "synthetic-owner", "department": "public",
        })
        ids.append(result["trace_id"])
    tracing.flush()
    base = os.environ["LANGFUSE_BASE_URL"].rstrip("/")
    with httpx.Client(base_url=base, auth=(os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"]),
                      timeout=10, trust_env=False) as client:
        deadline = time.monotonic() + 90
        pending = set(ids)
        observed = []
        while pending and time.monotonic() < deadline:
            for trace_id in list(pending):
                response = client.get("/api/public/traces/" + trace_id)
                if response.status_code == 200 and response.json().get("observations"):
                    observed.append(response.json())
                    pending.remove(trace_id)
            if pending:
                time.sleep(2)
        assert not pending, "Langfuse did not ingest every trace within 90 seconds"
        raw = json.dumps(observed)
        assert pii not in raw and "<PHONE_NUMBER>" in raw
        for trace in observed:
            names = {o["name"] for o in trace["observations"]}
            assert {"retrieve", "rerank", "llm"} <= names
            if trace["name"] == "/ask/jobs":
                assert {"queue_wait", "processing"} <= names
        (tmp_path / "trace-ids.json").write_text(json.dumps(ids))
    connection.close()
    qdrant.close()
