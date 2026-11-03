import os
from types import SimpleNamespace

import fakeredis
import pytest

os.environ.setdefault("RAG_BACKEND", "fake")
os.environ.setdefault("LLM_BACKEND", "fake")
os.environ.setdefault("AUTH_BACKEND", "fake")


@pytest.fixture(autouse=True)
def isolated_audit_db(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_DB_PATH", str(tmp_path / "audit.db"))


@pytest.fixture(autouse=True)
def isolated_api_redis(request, monkeypatch):
    """Exercise the real rate limiter without sharing Redis state between tests."""
    if request.node.get_closest_marker("integration"):
        yield None
        return
    from app.queue import jobs

    connection = fakeredis.FakeRedis()
    jobs.get_job_queue.cache_clear()
    monkeypatch.setattr(jobs, "Redis", SimpleNamespace(from_url=lambda *args, **kwargs: connection))
    yield connection
    jobs.get_job_queue.cache_clear()
    connection.close()
