"""Exercise HTTP + actual RQ persistence/execution against fakeredis."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import fakeredis
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError
from rq import SimpleWorker
from rq.job import Job
from rq.serializers import JSONSerializer
from rq.timeouts import TimerDeathPenalty

from app.contracts import AskResult, Citation, User
from app.main import create_app
from app.queue import jobs
from app.schemas import AskRequest

PII = "079123456789"
OWNER = User("owner@example.com", "credit")


@pytest.fixture
def api():
    connection = fakeredis.FakeRedis()
    queue = jobs.JobQueue(connection, max_length=3)
    application = create_app()
    application.dependency_overrides[jobs.get_job_queue] = lambda: queue
    application.dependency_overrides[jobs.get_current_user] = lambda: OWNER
    with TestClient(application) as client:
        yield client, queue, application
    connection.close()


def enqueue(client, **fields):
    return client.post("/ask/jobs", json={"question": "Annual fee?", **fields})


def fetch(queue, job_id):
    return Job.fetch(job_id, connection=queue.connection, serializer=JSONSerializer)


def work(queue):
    worker = SimpleWorker([queue.queue], connection=queue.connection, serializer=JSONSerializer)
    worker.death_penalty_class = TimerDeathPenalty
    worker.work(burst=True, with_scheduler=False)


def redis_contents(connection):
    # Include all Redis types (job payloads, meta, results and failures).
    return b"\n".join(connection.dump(key) for key in connection.scan_iter())


def test_accepts_masked_payload_and_tracks_position(api):
    client, queue, _ = api
    response = enqueue(client, question=f"CCCD {PII}", mode="dense", top_k=7, force_local=True)
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["position"] == 1
    job = fetch(queue, accepted["job_id"])
    payload, identity = job.args
    assert PII not in payload["question"]
    assert payload["mode"] == "dense" and payload["top_k"] == 7 and payload["force_local"] is True
    assert identity == {"user_id": jobs.owner_id(OWNER), "department": "credit", "role": "staff"}
    assert job.result_ttl == job.failure_ttl == 3600
    assert job.description == "Masked ask request"
    stored = redis_contents(queue.connection)
    assert PII.encode() not in stored and OWNER.user_id.encode() not in stored
    assert enqueue(client).json()["position"] == 2
    status = client.get(f"/ask/jobs/{accepted['job_id']}").json()
    assert status == {"job_id": job.id, "status": "queued", "position": 1, "result": None, "error": None}


@pytest.mark.parametrize("state", ["queued", "started", "finished", "failed"])
def test_owner_only_and_indistinguishable_404(api, state):
    client, queue, application = api
    job_id = enqueue(client).json()["job_id"]
    fetch(queue, job_id).set_status(state)
    application.dependency_overrides[jobs.get_current_user] = lambda: replace(OWNER, user_id="other@example.com")
    denied = client.get(f"/ask/jobs/{job_id}")
    missing = client.get(f"/ask/jobs/{uuid4()}")
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()


@pytest.mark.parametrize("job_id", ["bad-id", "rq:queue:ask", str(uuid4()).upper()])
def test_invalid_job_id_is_404(api, job_id):
    client, _, _ = api
    assert client.get(f"/ask/jobs/{job_id}").status_code == 404


def test_running_and_position_updates(api):
    client, queue, _ = api
    first = enqueue(client).json()["job_id"]
    second = enqueue(client).json()["job_id"]
    queue.queue.remove(first)
    fetch(queue, first).set_status("started")
    assert client.get(f"/ask/jobs/{first}").json()["status"] == "running"
    assert client.get(f"/ask/jobs/{first}").json()["position"] is None
    assert client.get(f"/ask/jobs/{second}").json()["position"] == 1


def test_queue_full_returns_503_without_orphans(api):
    client, queue, _ = api
    for _ in range(3):
        assert enqueue(client).status_code == 202
    before = set(queue.connection.scan_iter())
    response = enqueue(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert set(queue.connection.scan_iter()) == before


def test_concurrent_enqueue_cannot_exceed_capacity(api):
    _, queue, _ = api

    def submit(_):
        try:
            return queue.enqueue(AskRequest(question="Annual fee?"), OWNER)
        except HTTPException as exc:
            assert exc.status_code == 503
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = [result for result in pool.map(submit, range(12)) if result is not None]
    assert len(accepted) == queue.queue.count == 3
    assert sorted(result.position for result in accepted) == [1, 2, 3]
    assert len(list(queue.connection.scan_iter("rq:job:*"))) == 3


def test_finished_result_masked_in_redis_and_http_with_one_hour_ttl(api, monkeypatch):
    client, queue, _ = api
    calls = []

    class Answerer:
        def answer(self, question, user, mode):
            calls.append((question, user, mode))
            return AskResult(
                f"CCCD {PII}", True, [Citation(1, f"CCCD {PII}.pdf", 1, 0.9)],
                "dense", "cloud", 5, trace_id=PII,
            )

    monkeypatch.setattr(jobs, "get_answerer", lambda: Answerer())
    job_id = enqueue(client, question=f"CCCD {PII}", mode="dense").json()["job_id"]
    work(queue)
    response = client.get(f"/ask/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    result = response.json()["result"]
    assert result["found"] is True and result["citations"][0]["page"] == 1
    assert PII not in json.dumps(result)
    assert PII not in calls[0][0] and calls[0][1].department == "credit" and calls[0][2] == "dense"
    assert PII.encode() not in redis_contents(queue.connection)
    job = fetch(queue, job_id)
    assert PII not in json.dumps(job.return_value())
    assert 3590 <= queue.connection.ttl(job.key) <= 3600
    result_keys = list(queue.connection.scan_iter(f"rq:results:{job_id}"))
    assert len(result_keys) == 1
    assert 3590 <= queue.connection.ttl(result_keys[0]) <= 3600
    queue.connection.expire(job.key, 0)
    queue.connection.expire(result_keys[0], 0)
    assert client.get(f"/ask/jobs/{job_id}").status_code == 404


def test_failure_does_not_persist_or_return_upstream_pii(api, monkeypatch):
    client, queue, _ = api

    class BrokenAnswerer:
        def answer(self, *args):
            raise RuntimeError(f"Provider leaked {PII}")

    monkeypatch.setattr(jobs, "get_answerer", lambda: BrokenAnswerer())
    job_id = enqueue(client).json()["job_id"]
    work(queue)
    response = client.get(f"/ask/jobs/{job_id}")
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "Job execution failed"
    assert response.json()["result"] is None
    assert PII.encode() not in redis_contents(queue.connection)
    job = fetch(queue, job_id)
    failure = job.latest_result()
    assert PII not in failure.exc_string
    assert "Job execution failed" in failure.exc_string
    assert 3590 <= queue.connection.ttl(job.key) <= 3600


def test_masking_failure_enqueues_nothing(api, monkeypatch):
    client, queue, _ = api

    def unavailable(_):
        raise jobs.MaskingError("Unavailable")

    monkeypatch.setattr(jobs, "require_mask_text", unavailable)
    assert enqueue(client, question=f"CCCD {PII}").status_code == 503
    assert queue.queue.count == 0
    assert not list(queue.connection.scan_iter("rq:job:*"))


@pytest.mark.parametrize("method", ["post", "get"])
def test_redis_unavailable_returns_503(api, monkeypatch, method):
    client, queue, _ = api

    def unavailable(*args, **kwargs):
        raise ConnectionError(f"Backend leaked {PII}")

    monkeypatch.setattr(queue.connection, "execute_command", unavailable)
    monkeypatch.setattr(queue.connection, "pipeline", unavailable)
    response = enqueue(client) if method == "post" else client.get(f"/ask/jobs/{uuid4()}")
    assert response.status_code == 503
    assert PII not in response.text


@pytest.mark.parametrize("method", ["post", "get"])
def test_auth_required(api, monkeypatch, tmp_path, method):
    client, _, application = api
    registry = tmp_path / "keys.json"
    registry.write_text(json.dumps({
        hashlib.sha256(b"test-key").hexdigest(): {"user_id": "staff", "department": "hr", "role": "staff"},
    }))
    monkeypatch.setenv("AUTH_BACKEND", "apikey")
    monkeypatch.setenv("API_KEYS_FILE", str(registry))
    del application.dependency_overrides[jobs.get_current_user]
    path = "/ask/jobs" if method == "post" else f"/ask/jobs/{uuid4()}"
    for headers in ({}, {"X-API-Key": "invalid"}):
        response = client.post(path, json={"question": "Fee?"}, headers=headers) if method == "post" else client.get(
            path, headers=headers,
        )
        assert response.status_code == 401
    headers = {"X-API-Key": "test-key"}
    response = client.post(path, json={"question": "Fee?"}, headers=headers) if method == "post" else client.get(
        path, headers=headers,
    )
    assert response.status_code == (202 if method == "post" else 404)


def test_invalid_request_never_enqueued(api):
    client, queue, _ = api
    for body in ({}, {"question": ""}, {"question": "Fee?", "top_k": 21}, {"question": "Fee?", "mode": "invalid"}):
        assert client.post("/ask/jobs", json=body).status_code == 400
    assert queue.queue.count == 0
