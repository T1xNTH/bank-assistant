"""Shared bucket concurrency, worker retries and lifecycle edge cases."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import fakeredis
import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError
from rq.utils import utcformat

from app.contracts import User
from app.llm import LLMError, LLMRateLimitError
from app.queue import worker
from app.queue.jobs import JobQueue
from app.queue.limits import TokenBucket
from app.schemas import AskRequest


def test_bucket_shared_capacity_and_refill():
    connection = fakeredis.FakeRedis()
    # Use Redis state timestamps to simulate elapsed time without sleeping.
    buckets = [TokenBucket(connection, "rate:test", 60, 3) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        delays = list(pool.map(lambda bucket: bucket.take(), buckets))
    assert delays.count(0) == 3
    assert all(0 < delay <= 1 for delay in delays if delay)
    assert 1 <= connection.ttl("rate:test") <= 3
    seconds, micros = connection.time()
    connection.hset("rate:test", "updated", seconds + micros / 1_000_000 - 2)
    assert buckets[0].take() == 0


@pytest.mark.parametrize("rpm,capacity", [(0, 1), (1, 0), (-1, 2)])
def test_invalid_bucket_settings(rpm, capacity):
    with pytest.raises(ValueError):
        TokenBucket(fakeredis.FakeRedis(), "rate", rpm, capacity)


def test_worker_exponential_backoff_and_tokens_for_every_attempt(monkeypatch):
    tokens, sleeps, calls = [], [], []
    monkeypatch.setattr(worker.TokenBucket, "acquire", lambda self: tokens.append(self.key))
    monkeypatch.setattr(worker.time, "sleep", sleeps.append)
    monkeypatch.setenv("WORKER_MAX_ATTEMPTS", "4")

    def action():
        calls.append(1)
        if len(calls) < 4:
            raise LLMRateLimitError("Synthetic 429")
        return "done"

    assert worker.run_with_policy(action, fakeredis.FakeRedis()) == "done"
    assert sleeps == [1, 2, 4]
    assert len(tokens) == len(calls) == 4


@pytest.mark.parametrize("error", [LLMError("HTTP 503"), ValueError("private")])
def test_worker_does_not_retry_other_errors(monkeypatch, error):
    calls = []
    monkeypatch.setattr(worker.TokenBucket, "acquire", lambda self: calls.append(1))

    def action():
        raise error

    with pytest.raises(type(error)):
        worker.run_with_policy(action, fakeredis.FakeRedis())
    assert len(calls) == 1


def test_worker_retry_budget_and_limiter_outage(monkeypatch):
    calls = []
    monkeypatch.setenv("WORKER_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(worker.TokenBucket, "acquire", lambda self: calls.append(1))
    monkeypatch.setattr(worker.time, "sleep", lambda _: None)

    def action():
        raise LLMRateLimitError("429")

    with pytest.raises(LLMRateLimitError):
        worker.run_with_policy(action, fakeredis.FakeRedis())
    assert len(calls) == 2

    def unavailable(self):
        raise ConnectionError("Unavailable")

    monkeypatch.setattr(worker.TokenBucket, "acquire", unavailable)
    with pytest.raises(ConnectionError):
        worker.run_with_policy(lambda: pytest.fail("Must fail closed"), fakeredis.FakeRedis())


def test_queue_capacity_covers_priorities_and_reclaims_expired_jobs():
    connection = fakeredis.FakeRedis()
    queue = JobQueue(connection, max_length=2, waiting_ttl=30)
    user = User("owner", "public")
    request = AskRequest(question="Annual fee?")
    default = queue.enqueue(request, user)
    high = queue.enqueue(request, replace(user, role="approver"))
    assert high.position == 1
    assert queue.status(default.job_id, user).position == 2
    assert 0 < connection.ttl(f"rq:job:{high.job_id}") <= 30
    with pytest.raises(HTTPException) as error:
        queue.enqueue(request, user)
    assert error.value.status_code == 503
    connection.expire(f"rq:job:{high.job_id}", 0)
    with pytest.raises(HTTPException) as error:
        queue.status(high.job_id, user)
    assert error.value.status_code == 404
    assert queue.enqueue(request, user).position == 2
    assert queue.queues["ask-high"].count == 0


def test_legacy_jobs_visible_and_count_toward_capacity():
    connection = fakeredis.FakeRedis()
    queue = JobQueue(connection, max_length=1)
    user = User("owner", "public")
    # Simulate a pre-upgrade job by switching the producer to the legacy queue.
    queue.queue = queue.queues["ask"]
    job = queue.enqueue(AskRequest(question="Legacy?"), user)
    assert queue.status(job.job_id, user).status == "queued"
    queue.queue = queue.queues["ask-default"]
    with pytest.raises(HTTPException) as error:
        queue.enqueue(AskRequest(question="New?"), user)
    assert error.value.status_code == 503


@pytest.mark.parametrize("state", ["live", "missing", "other", "stale", "stopped", "outage"])
def test_healthcheck_requires_own_fresh_registration(monkeypatch, state):
    connection = fakeredis.FakeRedis()
    name = "another-replica" if state == "other" else worker.worker_name()
    registered = worker.Worker(worker.QUEUE_NAMES, name=name, connection=connection)
    if state != "missing":
        registered.register_birth()
    if state == "stale":
        stale = utcformat(datetime.now(timezone.utc) - timedelta(seconds=1000))
        connection.hset(registered.key, "last_heartbeat", stale)
    elif state == "stopped":
        connection.hset(registered.key, "state", "stopped")
    elif state == "outage":
        def unavailable(*args, **kwargs):
            raise ConnectionError("Unavailable")
        monkeypatch.setattr(connection, "hgetall", unavailable)
    monkeypatch.setattr(worker.Redis, "from_url", lambda *args, **kwargs: connection)
    assert worker.healthy() == (state == "live")
