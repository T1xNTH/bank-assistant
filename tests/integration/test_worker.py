"""Actual Redis, RQ execution and HTTP polling; no paid providers or RAG models."""

import os
import secrets
import subprocess
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from redis import Redis
from redis.exceptions import ConnectionError
from rq import SimpleWorker
from rq.serializers import JSONSerializer

from app.contracts import Hit, LLMResult, User
from app.llm import LLMRateLimitError
from app.main import create_app
from app.queue import jobs
from app.queue.limits import TokenBucket
from app.rag.answer import RagAnswerer
from app.schemas import AskRequest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def redis_connection():
    name = "bank-t025-test-" + secrets.token_hex(5)
    connection = None
    try:
        subprocess.run(
            ["docker", "run", "--rm", "-d", "--name", name,
             "-p", "127.0.0.1::6379", "redis:7.4-alpine"],
            check=True, capture_output=True, timeout=90,
        )
        published = subprocess.check_output(["docker", "port", name, "6379/tcp"], text=True).strip()
        connection = Redis(host="127.0.0.1", port=int(published.rsplit(":", 1)[1]), socket_timeout=2)
        for attempt in range(50):
            try:
                if connection.ping():
                    break
            except ConnectionError:
                if attempt == 49:
                    raise
                time.sleep(0.1)
        yield connection
    finally:
        if connection is not None:
            connection.close()
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)


def make_api(connection):
    queue = jobs.JobQueue(connection, max_length=100)
    app = create_app()
    app.dependency_overrides[jobs.get_job_queue] = lambda: queue
    app.dependency_overrides[jobs.get_current_user] = lambda: User("test-owner", "public")
    return app, queue


def test_burst_30_jobs_completes_with_zero_failures_against_429_fake_llm(redis_connection, monkeypatch):
    calls = Counter()

    class RateLimitedFakeLLM:
        def chat(self, messages, alias, temperature=0.0):
            question = messages[-1]["content"]
            calls[question] += 1
            if calls[question] <= 2:
                raise LLMRateLimitError("Synthetic HTTP 429")
            return LLMResult("Answer [1].", "fake/worker-test")

    answerer = RagAnswerer(
        retrieve=lambda *args: [Hit("doc", "safe.pdf", 1, "Annual fee", 0.9, "public")],
        llm=RateLimitedFakeLLM(),
    )
    monkeypatch.setattr(jobs, "get_answerer", lambda: answerer)
    monkeypatch.setenv("WORKER_RPM", "60000")
    monkeypatch.setenv("WORKER_BACKOFF_SECONDS", "0.001")
    monkeypatch.setenv("API_KEY_BURST", "30")
    app, queue = make_api(redis_connection)
    with TestClient(app) as client:
        accepted = [client.post("/ask/jobs", json={"question": f"Annual fee item {i}?"}) for i in range(30)]
        assert all(response.status_code == 202 for response in accepted)
        worker = SimpleWorker(list(queue.queues.values()), connection=redis_connection, serializer=JSONSerializer)
        worker.work(burst=True, with_scheduler=False)
        results = [client.get(f"/ask/jobs/{response.json()['job_id']}") for response in accepted]
        assert all(response.status_code == 200 and response.json()["status"] == "done" for response in results)
        assert all(response.json()["result"]["found"] for response in results)
        assert len(calls) == 30 and set(calls.values()) == {3}
        assert all(q.failed_job_registry.count == 0 for q in queue.queues.values())


def test_production_entrypoint_post_worker_poll_and_masked_storage(redis_connection, monkeypatch):
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{redis_connection.connection_pool.connection_kwargs['port']}/0")
    app, _ = make_api(redis_connection)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "RAG_BACKEND": "fake", "LLM_BACKEND": "fake"}
    # Withhold worker output: it must never accidentally expose host configuration.
    process = subprocess.Popen(
        [sys.executable, "-m", "app.queue.worker"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        with TestClient(app) as client:
            accepted = client.post("/ask/jobs", json={"question": "CCCD 000000000001"})
            assert accepted.status_code == 202
            job_id = accepted.json()["job_id"]
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                response = client.get(f"/ask/jobs/{job_id}")
                assert response.status_code == 200
                if response.json()["status"] in {"done", "failed"}:
                    break
                assert process.poll() is None, "Worker exited before completing the job"
                time.sleep(0.1)
            assert response.json()["status"] == "done"
            health = subprocess.run(
                [sys.executable, "-m", "app.queue.worker", "--healthcheck"],
                cwd=ROOT, env=env, capture_output=True, timeout=15,
            )
            assert health.returncode == 0, "Production worker healthcheck failed"
            assert b"000000000001" not in b"".join(redis_connection.dump(key) for key in redis_connection.scan_iter())
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_waiting_expiry_recovers_capacity_without_worker(redis_connection):
    queue = jobs.JobQueue(redis_connection, max_length=1, waiting_ttl=1)
    user = User("owner", "public")
    request = AskRequest(question="Fee?")
    expired = queue.enqueue(request, user)
    time.sleep(1.1)
    with pytest.raises(HTTPException) as error:
        queue.status(expired.job_id, user)
    assert error.value.status_code == 404
    accepted = queue.enqueue(request, user)
    assert accepted.position == queue.queue.count == 1
    assert queue.queue.get_job_ids() == [accepted.job_id]


def test_actual_worker_consumes_high_before_default_and_legacy(redis_connection, monkeypatch):
    calls = []
    from app.fakes_runtime import CannedAnswerer

    class RecordingAnswerer:
        def answer(self, question, user, mode):
            calls.append(question)
            return CannedAnswerer().answer(question, user, mode)

    monkeypatch.setattr(jobs, "get_answerer", RecordingAnswerer)
    monkeypatch.setenv("WORKER_RPM", "60000")
    queue = jobs.JobQueue(redis_connection)
    user = User("owner", "public")
    queue.queue = queue.queues["ask"]
    queue.enqueue(AskRequest(question="Legacy"), user)
    queue.queue = queue.queues["ask-default"]
    queue.enqueue(AskRequest(question="Default"), user)
    queue.enqueue(AskRequest(question="High"), replace(user, role="approver"))
    SimpleWorker(list(queue.queues.values()), connection=redis_connection, serializer=JSONSerializer).work(burst=True)
    assert calls == ["High", "Default", "Legacy"]


def test_worker_bucket_is_shared_and_spaces_real_attempts(redis_connection):
    first = TokenBucket(redis_connection, "ask:worker:rate", 600)
    second_connection = Redis(connection_pool=redis_connection.connection_pool)
    second = TokenBucket(second_connection, "ask:worker:rate", 600)
    first.acquire()
    started = time.monotonic()
    second.acquire()
    assert time.monotonic() - started >= 0.08
